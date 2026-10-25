package org.jellyfin.androidtv.kinolel

import android.app.LocaleManager
import android.content.Context
import android.content.res.Configuration
import android.os.Build
import android.os.LocaleList
import androidx.core.os.ConfigurationCompat
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import org.jellyfin.sdk.api.client.ApiClient
import org.jellyfin.sdk.api.client.extensions.displayPreferencesApi
import timber.log.Timber
import java.util.Locale

/**
 * Sprache der Oberfläche je Konto: Auf kinolel.de merkt sich KinoLel die Wahl Deutsch/Magyar beim Konto
 * (Anzeige-Einstellungen „usersettings“, Client „emby“, Eintrag „kl-sprache“, siehe kinolel.js).
 * Ist sie gesetzt, nimmt die TV-App dieselbe Sprache (Android 13+, App-Sprache); sonst bleibt es bei der Sprache des
 * Fernsehers bzw. der in den Android-Einstellungen für KinoLel gewählten.
 *
 * Lel 25.10. („Sind Updatenachrichten auch auf Ungarisch … wenn die ausgewählte Sprache auf Ungarisch ist?“): Die eigenen
 * Texte (Was ist neu, Update-Hinweis, Meldungen) folgen zuerst dieser Sprache – auch vor Android 13, dort über
 * [inKinoLelSprache]. Die Sprache wird auf dem Gerät gemerkt, damit sie beim nächsten Start sofort bekannt ist.
 */
object Sprache {
	private const val GEMERKT = "konto_sprache"
	private const val FRIST_MS = 5_000L
	private val erlaubt = setOf("de", "hu", "en")

	/** Zuletzt beim Konto gelesene Sprache (null: im Konto keine gewählt bzw. noch nicht angemeldet) */
	fun gemerkt(context: Context): String? =
		context.getSharedPreferences(Marke.EINSTELLUNGEN, Context.MODE_PRIVATE).getString(GEMERKT, null)?.takeIf { it in erlaubt }

	/**
	 * Sprache des Kontos lesen und übernehmen (höchstens [FRIST_MS] warten).
	 * true: Die App-Sprache wurde gerade umgestellt – Android baut die Activity neu auf, Meldungen erst danach zeigen.
	 */
	suspend fun ausKonto(context: Context, api: ApiClient): Boolean {
		val gelesen = withTimeoutOrNull(FRIST_MS) {
			runCatching {
				withContext(Dispatchers.IO) {
					api.displayPreferencesApi.getDisplayPreferences(displayPreferencesId = "usersettings", client = "emby").content
				}.customPrefs["kl-sprache"]?.takeIf { it in erlaubt }
			}.onFailure { Timber.w(it, "KinoLel: Sprache des Kontos nicht lesbar") }
		}
		// nicht erreichbar oder zu langsam: bei der gemerkten Sprache bleiben
		val wunsch = gelesen?.getOrNull()
		if (gelesen == null || gelesen.isFailure) return false
		context.getSharedPreferences(Marke.EINSTELLUNGEN, Context.MODE_PRIVATE).edit().putString(GEMERKT, wunsch).apply()

		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU || wunsch == null) return false
		val verwaltung = context.getSystemService(LocaleManager::class.java) ?: return false
		val aktuell = verwaltung.applicationLocales
		return when {
			!aktuell.isEmpty && aktuell[0].language == wunsch -> false
			aktuell.isEmpty && geraet(context) == wunsch -> false
			else -> {
				Timber.i("KinoLel: Sprache des Kontos $wunsch")
				verwaltung.applicationLocales = LocaleList.forLanguageTags(wunsch)
				true
			}
		}
	}

	/** Sprache der Oberfläche laut Android (App-Sprache bzw. Fernseher): de, hu, sonst en */
	fun geraet(context: Context): String = when (ConfigurationCompat.getLocales(context.resources.configuration)[0]?.language) {
		"hu" -> "hu"
		"de" -> "de"
		else -> "en"
	}

	/** KinoLel-Sprache: die im Konto gewählte, sonst die der Oberfläche */
	fun aktuell(context: Context): String = gemerkt(context) ?: geraet(context)

	/** Kontext, dessen Texte (getString) in der KinoLel-Sprache sind */
	fun kontext(context: Context): Context {
		val sprache = aktuell(context)
		if (geraet(context) == sprache) return context
		val konfiguration = Configuration(context.resources.configuration).apply { setLocale(Locale(sprache)) }
		return context.createConfigurationContext(konfiguration)
	}
}

/** Texte der KinoLel-Zusätze in der Sprache des Kontos (siehe [Sprache]) */
val Context.inKinoLelSprache: Context get() = Sprache.kontext(this)
