package org.jellyfin.androidtv.kinolel

import android.content.Context
import org.jellyfin.androidtv.BuildConfig
import org.jellyfin.androidtv.R
import org.json.JSONObject
import timber.log.Timber

/**
 * „Was ist neu“ wie in den anderen KinoLel-Apps: einmalig nach einem Update ein Dialog mit den Neuerungen.
 *
 * Die Texte liegen in der App (assets/kinolel/neuigkeiten.json, je Version de/hu/en) – funktioniert also auch offline.
 * Gezeigt werden alle Einträge, die neuer sind als die zuletzt gesehene Version, höchstens bis zur installierten.
 * Frisch installiert: nichts zeigen.
 */
object Neuigkeiten {
	private const val GESEHEN = "neuigkeiten_gesehen"
	private const val DATEI = "kinolel/neuigkeiten.json"

	fun zeigenFallsNeu(context: Context) {
		val einstellungen = context.getSharedPreferences(Marke.EINSTELLUNGEN, Context.MODE_PRIVATE)
		val aktuell = version(BuildConfig.VERSION_NAME)
		val gesehenText = einstellungen.getString(GESEHEN, null)
		if (gesehenText != null && vergleiche(version(gesehenText), aktuell) >= 0) return
		einstellungen.edit().putString(GESEHEN, aktuell.joinToString(".")).apply()

		// Frisch installiert (noch nie aktualisiert) -> keine Meldung
		val aktualisiert = gesehenText != null || runCatching {
			val info = context.packageManager.getPackageInfo(context.packageName, 0)
			info.lastUpdateTime > info.firstInstallTime
		}.getOrDefault(false)
		if (!aktualisiert) return

		val eintraege = runCatching { lesen(context, Marke.sprache(context)) }
			.onFailure { Timber.w(it, "KinoLel: Neuigkeiten") }
			.getOrNull() ?: return
		val passend = eintraege
			.filter { (v, _) -> vergleiche(v, aktuell) <= 0 }
			.let { liste -> if (gesehenText != null) liste.filter { (v, _) -> vergleiche(v, version(gesehenText)) > 0 } else liste.take(2) }
		if (passend.isEmpty()) return

		val text = buildString {
			passend.forEachIndexed { i, (v, punkte) ->
				if (passend.size > 1) {
					if (i > 0) append("\n")
					append(context.getString(R.string.kinolel_neu_version, v.joinToString("."))).append("\n")
				}
				punkte.forEach { append("• ").append(it).append("\n") }
			}
		}.trimEnd('\n')

		KinoLelMeldungen.zeigen(
			KinoLelMeldung(
				titel = context.getString(R.string.kinolel_neu_titel, aktuell.joinToString(".")),
				text = text,
				kennung = "kinolel.neuigkeiten",
				knoepfe = listOf(KinoLelKnopf(context.getString(R.string.kinolel_neu_ok), haupt = true, kennung = "kinolel.neuigkeiten.ok")),
			)
		)
	}

	/** Einträge (neueste zuerst): Version -> Stichpunkte in der Sprache (Ersatz: Deutsch). */
	private fun lesen(context: Context, sprache: String): List<Pair<List<Int>, List<String>>> {
		val json = context.assets.open(DATEI).bufferedReader().use { it.readText() }
		val versionen = JSONObject(json).getJSONArray("versionen")
		return (0 until versionen.length()).map { i ->
			val eintrag = versionen.getJSONObject(i)
			val punkte = eintrag.optJSONArray(sprache) ?: eintrag.getJSONArray("de")
			version(eintrag.getString("version")) to (0 until punkte.length()).map { punkte.getString(it) }
		}.sortedWith { a, b -> vergleiche(b.first, a.first) }
	}

	private fun version(text: String): List<Int> =
		text.trim().removePrefix("v").substringBefore('-').split('.').map { it.toIntOrNull() ?: 0 }

	private fun vergleiche(a: List<Int>, b: List<Int>): Int {
		for (i in 0 until maxOf(a.size, b.size)) {
			val unterschied = a.getOrElse(i) { 0 } - b.getOrElse(i) { 0 }
			if (unterschied != 0) return unterschied
		}
		return 0
	}
}
