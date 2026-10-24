package org.jellyfin.androidtv.kinolel

import android.app.LocaleManager
import android.content.Context
import android.os.Build
import android.os.LocaleList
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.jellyfin.sdk.api.client.ApiClient
import org.jellyfin.sdk.api.client.extensions.displayPreferencesApi
import timber.log.Timber

/**
 * Sprache der Oberfläche je Konto: Auf kinolel.de merkt sich KinoLel die Wahl Deutsch/Magyar beim Konto
 * (Anzeige-Einstellungen „usersettings“, Client „emby“, Eintrag „kl-sprache“, siehe kinolel.js).
 * Ist sie gesetzt, nimmt die TV-App dieselbe Sprache (Android 13+, App-Sprache); sonst bleibt es bei der Sprache des
 * Fernsehers bzw. der in den Android-Einstellungen für KinoLel gewählten.
 */
object Sprache {
	private val erlaubt = setOf("de", "hu", "en")

	suspend fun ausKonto(context: Context, api: ApiClient) {
		if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) return
		val wunsch = runCatching {
			withContext(Dispatchers.IO) {
				api.displayPreferencesApi.getDisplayPreferences(displayPreferencesId = "usersettings", client = "emby").content
			}.customPrefs["kl-sprache"]?.takeIf { it in erlaubt }
		}.onFailure { Timber.w(it, "KinoLel: Sprache des Kontos nicht lesbar") }.getOrElse { return }

		val verwaltung = context.getSystemService(LocaleManager::class.java) ?: return
		val aktuell = verwaltung.applicationLocales
		when {
			// Konto ohne gemerkte Sprache: nichts ändern (Fernseher-Sprache oder die in den Android-Einstellungen gewählte)
			wunsch == null -> Unit
			!aktuell.isEmpty && aktuell[0].language == wunsch -> Unit
			aktuell.isEmpty && Marke.sprache(context) == wunsch -> Unit
			else -> {
				Timber.i("KinoLel: Sprache des Kontos $wunsch")
				verwaltung.applicationLocales = LocaleList.forLanguageTags(wunsch)
			}
		}
	}
}
