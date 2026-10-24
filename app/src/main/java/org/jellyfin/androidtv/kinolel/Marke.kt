package org.jellyfin.androidtv.kinolel

import android.content.Context
import androidx.core.os.ConfigurationCompat
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

	/** Quick Connect am Handy: Jellyfins Seite übernimmt den Code aus der Adresse. */
	fun quickConnectAdresse(code: String) = "$SERVER/web/#/quickconnect?code=$code"

	/** Sprache der Oberfläche: folgt der Sprache des Fernsehers (Jellyfin speichert keine Sprache je Benutzer). */
	fun sprache(context: Context): String = when (ConfigurationCompat.getLocales(context.resources.configuration)[0]?.language) {
		"hu" -> "hu"
		"de" -> "de"
		else -> "en"
	}

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
