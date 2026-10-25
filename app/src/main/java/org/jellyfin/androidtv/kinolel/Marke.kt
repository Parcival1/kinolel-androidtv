package org.jellyfin.androidtv.kinolel

import android.content.Context
import org.jellyfin.androidtv.BuildConfig

/**
 * KinoLel TV: alles, was die Marke ausmacht (Werte aus marke.properties, siehe app/build.gradle.kts).
 */
object Marke {
	/** Fester Server – es gibt keine Serverauswahl. */
	const val SERVER = BuildConfig.KINOLEL_SERVER
	const val APPS_LISTE = BuildConfig.KINOLEL_APPS_LISTE
	const val APPS_SCHLUESSEL = BuildConfig.KINOLEL_APPS_SCHLUESSEL
	const val UPDATE_REPO = BuildConfig.KINOLEL_UPDATE_REPO
	const val WUENSCHE = BuildConfig.KINOLEL_WUENSCHE
	const val WUENSCHE_HU = BuildConfig.KINOLEL_WUENSCHE_HU
	const val HILFE = BuildConfig.KINOLEL_HILFE

	/** Einstellungen der KinoLel-Zusätze (nur auf diesem Gerät). */
	const val EINSTELLUNGEN = "kinolel"

	/**
	 * Quick Connect am Handy (Lel 24.10.): Mit KinoLel-Android-App öffnet der Link direkt die App (App Link für
	 * /web/kinolel/qc, Fragmente wie #/quickconnect zählen dafür nicht), sonst leitet qc.html im Browser auf Jellyfins
	 * Quick-Connect-Seite weiter. Beide tragen den Code ein, „Autorisieren“ tippt der Nutzer selbst.
	 */
	fun quickConnectAdresse(code: String) = "$SERVER/web/kinolel/qc.html?code=$code"

	/** Sprache der KinoLel-Texte: die im Konto gewählte (kinolel.de), sonst die der Oberfläche – siehe [Sprache]. */
	fun sprache(context: Context): String = Sprache.aktuell(context)

	fun ungarisch(context: Context) = sprache(context) == "hu"

	/**
	 * Texte vom Server kommen oft zweisprachig „Deutsch / Ungarisch“ (z. B. der Hinweis zur Wiedergabe-Grenze).
	 * Zeigt nur den Teil in der Sprache der Oberfläche.
	 */
	fun passenderTeil(context: Context, text: String): String {
		val teile = text.split(" / ").map(String::trim).filter(String::isNotEmpty)
		if (teile.size != 2) return text
		return if (ungarisch(context)) teile[1] else teile[0]
	}
}
