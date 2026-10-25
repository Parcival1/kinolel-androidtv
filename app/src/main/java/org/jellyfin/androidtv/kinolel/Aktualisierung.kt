package org.jellyfin.androidtv.kinolel

import android.app.PendingIntent
import android.content.ActivityNotFoundException
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageInstaller
import android.net.Uri
import android.os.Build
import android.provider.Settings
import android.widget.Toast
import androidx.lifecycle.ProcessLifecycleOwner
import androidx.lifecycle.lifecycleScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.jellyfin.androidtv.BuildConfig
import org.jellyfin.androidtv.R
import timber.log.Timber
import java.io.File
import java.net.HttpURLConnection
import java.net.URL

/**
 * Update-Prüfung wie in der KinoLel-Android-App: bei jedem Start (höchstens einmal pro Minute) die Liste
 * https://kinolel.de/web/kinolel/apps.json lesen (Schlüssel „androidtv“), GitHub nur als Rückfall.
 * „Später“ fragt erst nach 4 Stunden wieder. „Aktualisieren“ lädt die APK und startet die Installation.
 */
object Aktualisierung {
	private const val MIN_ABSTAND_MS = 60_000L
	private const val SPAETER_MS = 4 * 60 * 60 * 1000L
	private const val KENNUNG = "kinolel.update"

	data class NeueVersion(val version: String, val apk: String)

	@Volatile
	private var zuletzt = 0L

	/** Für Tests (nur Debug-Version): andere apps.json, gesetzt in den KinoLel-Einstellungen (Schlüssel „apps_liste“). */
	private fun liste(context: Context): String =
		if (BuildConfig.DEBUG) einstellungen(context).getString("apps_liste", null) ?: Marke.APPS_LISTE
		else Marke.APPS_LISTE

	private fun einstellungen(context: Context) = context.getSharedPreferences(Marke.EINSTELLUNGEN, Context.MODE_PRIVATE)

	suspend fun pruefen(context: Context, vonHand: Boolean = false) {
		val jetzt = System.currentTimeMillis()
		if (!vonHand) {
			if (jetzt - zuletzt < MIN_ABSTAND_MS) return
			if (jetzt < einstellungen(context).getLong("spaeter_bis", 0)) return
			if (KinoLelMeldungen.offen(KENNUNG)) return
		}
		zuletzt = jetzt

		val neu = withContext(Dispatchers.IO) {
			runCatching { ausListe(context) }.onFailure { Timber.w(it, "KinoLel: apps.json nicht lesbar") }.getOrNull()
				?: runCatching { ausGithub() }.onFailure { Timber.w(it, "KinoLel: GitHub nicht erreichbar") }.getOrNull()
		}
		Timber.i("KinoLel: Update-Prüfung – installiert ${BuildConfig.VERSION_NAME}, verfügbar ${neu?.version}")

		when {
			neu != null && neuer(neu.version, BuildConfig.VERSION_NAME) -> hinweis(context, neu)
			vonHand && neu != null -> Toast.makeText(context, context.inKinoLelSprache.getText(R.string.kinolel_update_aktuell), Toast.LENGTH_LONG).show()
			vonHand -> Toast.makeText(context, context.inKinoLelSprache.getText(R.string.kinolel_update_keine_verbindung), Toast.LENGTH_LONG).show()
		}
	}

	private fun lese(adresse: String): String {
		val verbindung = URL(adresse).openConnection() as HttpURLConnection
		verbindung.connectTimeout = 10_000
		verbindung.readTimeout = 15_000
		verbindung.setRequestProperty("Cache-Control", "no-cache")
		verbindung.setRequestProperty("User-Agent", "KinoLel-TV/${BuildConfig.VERSION_NAME}")
		try {
			if (verbindung.responseCode != HttpURLConnection.HTTP_OK) error("HTTP ${verbindung.responseCode}")
			return verbindung.inputStream.bufferedReader().use { it.readText() }
		} finally {
			verbindung.disconnect()
		}
	}

	private fun ausListe(context: Context): NeueVersion? {
		val eintrag = Json.parseToJsonElement(lese(liste(context))).jsonObject[Marke.APPS_SCHLUESSEL] as? JsonObject ?: return null
		val version = eintrag["version"]?.jsonPrimitive?.content?.removePrefix("v") ?: return null
		val apk = eintrag["url"]?.jsonPrimitive?.content ?: return null
		return NeueVersion(version, apk)
	}

	private fun ausGithub(): NeueVersion? {
		val release = Json.parseToJsonElement(lese("https://api.github.com/repos/${Marke.UPDATE_REPO}/releases/latest")).jsonObject
		val version = release["tag_name"]?.jsonPrimitive?.content?.removePrefix("v") ?: return null
		val apk = release["assets"]?.jsonArray
			?.map { it.jsonObject }
			?.firstOrNull { it["name"]?.jsonPrimitive?.content?.endsWith(".apk") == true }
			?.get("browser_download_url")?.jsonPrimitive?.content ?: return null
		return NeueVersion(version, apk)
	}

	/** true, wenn [a] neuer ist als [b] (drei Zahlen, Zusätze wie „-dev“ zählen nicht). */
	fun neuer(a: String, b: String): Boolean {
		fun teile(v: String) = v.substringBefore('-').split('.').map { it.toIntOrNull() ?: 0 } + listOf(0, 0, 0)
		val x = teile(a)
		val y = teile(b)
		for (i in 0 until 3) if (x[i] != y[i]) return x[i] > y[i]
		return false
	}

	private fun hinweis(context: Context, neu: NeueVersion) {
		KinoLelMeldungen.zeigen(
			KinoLelMeldung(
				titel = context.inKinoLelSprache.getString(R.string.kinolel_update_titel),
				text = context.inKinoLelSprache.getString(R.string.kinolel_update_text, neu.version, BuildConfig.VERSION_NAME),
				kennung = KENNUNG,
				knoepfe = listOf(
					KinoLelKnopf(context.inKinoLelSprache.getString(R.string.kinolel_spaeter), kennung = "kinolel.update.spaeter") {
						einstellungen(context).edit().putLong("spaeter_bis", System.currentTimeMillis() + SPAETER_MS).apply()
					},
					KinoLelKnopf(context.inKinoLelSprache.getString(R.string.kinolel_update_jetzt), haupt = true, kennung = "kinolel.update.jetzt") {
						installieren(context.applicationContext, neu)
					},
				),
				beimSchliessen = {
					einstellungen(context).edit().putLong("spaeter_bis", System.currentTimeMillis() + SPAETER_MS).apply()
				},
			)
		)
	}

	/** Darf KinoLel Apps installieren? Sonst erst die Freigabe in den Einstellungen erklären. */
	private fun installieren(context: Context, neu: NeueVersion) {
		if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O && !context.packageManager.canRequestPackageInstalls()) {
			KinoLelMeldungen.zeigen(
				KinoLelMeldung(
					titel = context.inKinoLelSprache.getString(R.string.kinolel_update_freigabe_titel),
					text = context.inKinoLelSprache.getString(R.string.kinolel_update_freigabe_text),
					kennung = "kinolel.update.freigabe",
					knoepfe = listOf(
						KinoLelKnopf(context.inKinoLelSprache.getString(R.string.kinolel_abbrechen)),
						KinoLelKnopf(context.inKinoLelSprache.getString(R.string.kinolel_einstellungen_oeffnen), haupt = true) {
							einstellungenOeffnen(context)
						},
					),
				)
			)
			return
		}

		Toast.makeText(context, context.inKinoLelSprache.getString(R.string.kinolel_update_laedt, neu.version), Toast.LENGTH_LONG).show()
		ProcessLifecycleOwner.get().lifecycleScope.launch { installation(context, neu) }
	}

	private fun einstellungenOeffnen(context: Context) {
		val ziele = buildList {
			if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
				add(Intent(Settings.ACTION_MANAGE_UNKNOWN_APP_SOURCES, Uri.parse("package:${context.packageName}")))
			}
			add(Intent(Settings.ACTION_SECURITY_SETTINGS))
			add(Intent(Settings.ACTION_SETTINGS))
		}
		for (ziel in ziele) {
			try {
				context.startActivity(ziel.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
				return
			} catch (_: ActivityNotFoundException) {
			} catch (_: SecurityException) {
			}
		}
	}

	private suspend fun installation(context: Context, neu: NeueVersion) {
		val ok = withContext(Dispatchers.IO) {
			runCatching { uebergeben(context, laden(context, neu)) }
				.onFailure { Timber.e(it, "KinoLel: Update nicht geladen oder Installation nicht gestartet") }
				.isSuccess
		}
		if (!ok) Toast.makeText(context, context.inKinoLelSprache.getText(R.string.kinolel_update_fehler), Toast.LENGTH_LONG).show()
	}

	private fun laden(context: Context, neu: NeueVersion): File {
		val ordner = File(context.cacheDir, "aktualisierung").apply { deleteRecursively(); mkdirs() }
		val datei = File(ordner, "kinolel-tv-${neu.version}.apk")
		var adresse = neu.apk
		// GitHub leitet auf einen Speicherdienst um (andere Adresse) – Umleitungen selbst folgen
		repeat(5) {
			val verbindung = URL(adresse).openConnection() as HttpURLConnection
			verbindung.instanceFollowRedirects = false
			verbindung.connectTimeout = 15_000
			verbindung.readTimeout = 60_000
			try {
				when (verbindung.responseCode) {
					HttpURLConnection.HTTP_OK -> {
						verbindung.inputStream.use { ein -> datei.outputStream().use { aus -> ein.copyTo(aus) } }
						return datei
					}

					in 300..399 -> adresse = URL(URL(adresse), verbindung.getHeaderField("Location")).toString()
					else -> error("HTTP ${verbindung.responseCode}")
				}
			} finally {
				verbindung.disconnect()
			}
		}
		error("zu viele Umleitungen")
	}

	/** Übergabe an Android: zeigt die übliche Abfrage „Diese App aktualisieren?“. */
	private fun uebergeben(context: Context, datei: File) {
		val installer = context.packageManager.packageInstaller
		val parameter = PackageInstaller.SessionParams(PackageInstaller.SessionParams.MODE_FULL_INSTALL).apply {
			setAppPackageName(context.packageName)
		}
		val sitzung = installer.createSession(parameter)
		installer.openSession(sitzung).use { s ->
			s.openWrite("kinolel-tv.apk", 0, datei.length()).use { aus ->
				datei.inputStream().use { it.copyTo(aus) }
				s.fsync(aus)
			}
			val antwort = Intent(context, InstallationsAntwort::class.java).setPackage(context.packageName)
			val flags = PendingIntent.FLAG_UPDATE_CURRENT or
				(if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) PendingIntent.FLAG_MUTABLE else 0)
			s.commit(PendingIntent.getBroadcast(context, sitzung, antwort, flags).intentSender)
		}
	}
}

/** Antwort von Android auf die Installation: Bestätigung anzeigen oder Fehler melden. */
class InstallationsAntwort : BroadcastReceiver() {
	override fun onReceive(context: Context, intent: Intent) {
		when (val status = intent.getIntExtra(PackageInstaller.EXTRA_STATUS, PackageInstaller.STATUS_FAILURE)) {
			PackageInstaller.STATUS_PENDING_USER_ACTION -> {
				@Suppress("DEPRECATION")
				val bestaetigen = intent.getParcelableExtra<Intent>(Intent.EXTRA_INTENT) ?: return
				context.startActivity(bestaetigen.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK))
			}

			PackageInstaller.STATUS_SUCCESS -> Timber.i("KinoLel: Update installiert")
			else -> {
				Timber.w("KinoLel: Installation fehlgeschlagen ($status): ${intent.getStringExtra(PackageInstaller.EXTRA_STATUS_MESSAGE)}")
				Toast.makeText(context, context.inKinoLelSprache.getText(R.string.kinolel_update_fehler), Toast.LENGTH_LONG).show()
			}
		}
	}
}
