package org.jellyfin.androidtv.kinolel

import android.os.Bundle
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.fragment.app.Fragment
import androidx.fragment.compose.content
import kotlinx.coroutines.launch
import org.jellyfin.androidtv.BuildConfig
import org.jellyfin.androidtv.R
import org.jellyfin.androidtv.ui.base.Text
import org.jellyfin.androidtv.ui.base.button.Button
import org.jellyfin.androidtv.ui.shared.toolbar.MainToolbar
import org.jellyfin.androidtv.ui.shared.toolbar.MainToolbarActiveButton

/**
 * KinoLel-Seiten für die Fernbedienung: „Wünsche“ und „Hilfe“ als QR-Code (Tippen am Fernseher ist unzumutbar).
 * Argument [ARG_SEITE] = [WUENSCHE] oder [HILFE]; [ARG_OHNE_KOPF] = true auf dem Anmeldebildschirm (noch kein Konto).
 */
class KinoLelSeiteFragment : Fragment() {
	companion object {
		const val ARG_SEITE = "seite"
		const val ARG_OHNE_KOPF = "ohne_kopf"
		const val WUENSCHE = "wuensche"
		const val HILFE = "hilfe"
	}

	override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?) = content {
		val seite = arguments?.getString(ARG_SEITE) ?: HILFE
		val mitKopf = arguments?.getBoolean(ARG_OHNE_KOPF) != true

		Column(modifier = Modifier.fillMaxSize()) {
			if (mitKopf) MainToolbar(if (seite == WUENSCHE) MainToolbarActiveButton.Wuensche else MainToolbarActiveButton.Hilfe)
			Row(
				horizontalArrangement = Arrangement.spacedBy(56.dp),
				modifier = Modifier
					.fillMaxSize()
					.padding(horizontal = 64.dp, vertical = if (mitKopf) 8.dp else 48.dp),
			) {
				if (seite == WUENSCHE) WuenscheSeite() else HilfeSeite(mitKopf)
			}
		}
	}
}

@Composable
private fun Ueberschrift(text: String) = Text(
	text = text,
	color = KinoLelFarben.Text,
	fontSize = 34.sp,
	fontWeight = FontWeight.SemiBold,
)

@Composable
private fun Absatz(text: String, modifier: Modifier = Modifier) = Text(
	text = text,
	color = KinoLelFarben.TextLeise,
	fontSize = 20.sp,
	lineHeight = 30.sp,
	modifier = modifier,
)

@Composable
private fun QrMitText(adresse: String, beschriftung: String, groesse: Int) {
	Column(horizontalAlignment = Alignment.CenterHorizontally) {
		QrCode(text = adresse, groesse = groesse.dp)
		Spacer(Modifier.height(12.dp))
		Text(text = beschriftung, color = KinoLelFarben.Text, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
		Text(text = adresse.removePrefix("https://"), color = KinoLelFarben.TextLeise, fontSize = 16.sp)
	}
}

@Composable
private fun WuenscheSeite() {
	val context = LocalContext.current
	val ungarisch = remember { Marke.ungarisch(context) }

	Column(modifier = Modifier.widthIn(max = 520.dp).padding(top = 24.dp)) {
		Ueberschrift(stringResource(R.string.kinolel_wuensche))
		Spacer(Modifier.height(18.dp))
		Absatz(stringResource(R.string.kinolel_wuensche_text))
	}
	Row(horizontalArrangement = Arrangement.spacedBy(40.dp), modifier = Modifier.padding(top = 24.dp)) {
		// passendes Portal zuerst und größer
		val deutsch = Triple(Marke.WUENSCHE, "Deutsch", false)
		val magyar = Triple(Marke.WUENSCHE_HU, "Magyar", true)
		listOf(if (ungarisch) magyar else deutsch, if (ungarisch) deutsch else magyar).forEachIndexed { i, (adresse, name, _) ->
			QrMitText(adresse, name, if (i == 0) 230 else 150)
		}
	}
}

@Composable
private fun HilfeSeite(mitKopf: Boolean) {
	val context = LocalContext.current
	val bereich = rememberCoroutineScope()

	Column(modifier = Modifier.widthIn(max = 760.dp).padding(top = 8.dp)) {
		Ueberschrift(stringResource(R.string.kinolel_hilfe))
		Spacer(Modifier.height(14.dp))
		Absatz(stringResource(R.string.kinolel_hilfe_bedienung))
		Spacer(Modifier.height(14.dp))
		Absatz(stringResource(R.string.kinolel_hilfe_anmelden))
		Spacer(Modifier.height(14.dp))
		Absatz(stringResource(R.string.kinolel_hilfe_updates))
		Spacer(Modifier.height(20.dp))
		Row(verticalAlignment = Alignment.CenterVertically) {
			// Update-Suche nur nach der Anmeldung (dort zeigt die App ihre Meldungen)
			if (mitKopf) {
				Button(
					onClick = { bereich.launch { Aktualisierung.pruefen(context, vonHand = true) } },
					modifier = Modifier.semantics { contentDescription = "kinolel.hilfe.updates" },
				) {
					Text(stringResource(R.string.kinolel_update_suchen), fontSize = 18.sp)
				}
				Spacer(Modifier.width(20.dp))
			}
			Text(
				text = "KinoLel TV ${BuildConfig.VERSION_NAME}",
				color = KinoLelFarben.TextLeise,
				fontSize = 16.sp,
			)
		}
	}
	Column(modifier = Modifier.padding(top = 32.dp)) {
		QrMitText(Marke.HILFE, stringResource(R.string.kinolel_hilfe_qr), 210)
	}
}
