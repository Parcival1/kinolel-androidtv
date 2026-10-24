package org.jellyfin.androidtv.kinolel

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import org.jellyfin.androidtv.ui.base.Text
import org.jellyfin.androidtv.ui.base.button.Button
import org.jellyfin.androidtv.ui.base.button.ButtonDefaults
import org.jellyfin.androidtv.ui.base.dialog.DialogBase

/** Farben der KinoLel-Dialoge – wie in den anderen KinoLel-Apps (Android, iPhone, Windows). */
object KinoLelFarben {
	val Grund = Color(0xFF0B0F18)
	val GrundHell = Color(0xFF151B2A)
	val Dialog = Color(0xFF1B1D2A)
	val DialogRand = Color(0x14FFFFFF)
	val Lavendel = Color(0xFF9AA4FF)
	val Knopf = Color(0xFF6C72EE)
	val Text = Color(0xFFF1F2FA)
	val TextLeise = Color(0xFFB9BDD3)
}

/**
 * Ein Knopf im KinoLel-Dialog. [haupt] = gefüllter Lavendel-Knopf, bekommt beim Öffnen den Fokus.
 * [kennung] steht als Beschreibung im Knopf (für die automatischen Tests, die nur die Fernbedienung benutzen).
 */
data class KinoLelKnopf(
	val titel: String,
	val haupt: Boolean = false,
	val kennung: String = "",
	val aktion: () -> Unit = {},
)

data class KinoLelMeldung(
	val titel: String,
	val text: String,
	val knoepfe: List<KinoLelKnopf>,
	/** Nach so vielen Millisekunden von selbst schließen (0 = nie), z. B. Nachrichten vom Server. */
	val zeitMs: Long = 0,
	/** Wird aufgerufen, wenn die Meldung mit Zurück geschlossen wird. */
	val beimSchliessen: () -> Unit = {},
	val kennung: String = "",
)

/**
 * Warteschlange der KinoLel-Meldungen. Angezeigt werden sie von [KinoLelMeldungenAnzeige] (in MainActivity),
 * immer nur eine zugleich – die nächste erscheint, wenn die vorige geschlossen ist.
 */
object KinoLelMeldungen {
	private val _liste = MutableStateFlow<List<KinoLelMeldung>>(emptyList())
	val liste = _liste.asStateFlow()

	/** Wie viele Anzeigen gerade sichtbar sind (0 = keine Activity im Vordergrund, dann Rückfall auf Toast). */
	@Volatile
	var anzeigen = 0
		internal set

	fun zeigen(meldung: KinoLelMeldung) = _liste.update { liste ->
		// dieselbe Meldung (gleiche Kennung) nicht doppelt
		if (meldung.kennung.isNotEmpty() && liste.any { it.kennung == meldung.kennung }) liste else liste + meldung
	}

	fun schliessen(meldung: KinoLelMeldung) = _liste.update { it - meldung }

	fun offen(kennung: String) = _liste.value.any { it.kennung == kennung }
}

@Composable
fun KinoLelMeldungenAnzeige() {
	DisposableEffect(Unit) {
		KinoLelMeldungen.anzeigen++
		onDispose { KinoLelMeldungen.anzeigen-- }
	}

	val liste by KinoLelMeldungen.liste.collectAsState()
	val meldung = liste.firstOrNull()

	if (meldung != null) {
		KinoLelDialog(
			meldung = meldung,
			schliessen = { KinoLelMeldungen.schliessen(meldung) },
		)
	}
}

@Composable
fun KinoLelDialog(meldung: KinoLelMeldung, schliessen: () -> Unit) {
	val hauptFokus = remember(meldung) { FocusRequester() }

	if (meldung.zeitMs > 0) {
		LaunchedEffect(meldung) {
			delay(meldung.zeitMs)
			schliessen()
		}
	}

	DialogBase(
		visible = true,
		onDismissRequest = {
			schliessen()
			meldung.beimSchliessen()
		},
	) {
		Column(
			modifier = Modifier
				.widthIn(min = 420.dp, max = 720.dp)
				.clip(RoundedCornerShape(18.dp))
				.background(KinoLelFarben.Dialog)
				.border(1.dp, KinoLelFarben.DialogRand, RoundedCornerShape(18.dp))
				.padding(horizontal = 36.dp, vertical = 28.dp)
				.semantics { contentDescription = meldung.kennung.ifEmpty { "kinolel.dialog" } },
		) {
			Text(
				text = meldung.titel,
				color = KinoLelFarben.Text,
				fontSize = 26.sp,
				fontWeight = FontWeight.SemiBold,
			)
			Spacer(Modifier.height(14.dp))
			Column(
				modifier = Modifier
					.weight(1f, fill = false)
					.verticalScroll(rememberScrollState())
			) {
				Text(
					text = meldung.text,
					color = KinoLelFarben.TextLeise,
					fontSize = 19.sp,
					lineHeight = 28.sp,
				)
			}
			Spacer(Modifier.height(26.dp))
			Row(
				horizontalArrangement = Arrangement.spacedBy(14.dp, androidx.compose.ui.Alignment.End),
				modifier = Modifier.align(androidx.compose.ui.Alignment.End),
			) {
				meldung.knoepfe.forEach { knopf ->
					Button(
						onClick = {
							schliessen()
							knopf.aktion()
						},
						colors = if (knopf.haupt) ButtonDefaults.colors(
							containerColor = KinoLelFarben.Knopf,
							contentColor = Color.White,
							focusedContainerColor = KinoLelFarben.Lavendel,
							focusedContentColor = KinoLelFarben.Grund,
						) else ButtonDefaults.colors(),
						modifier = Modifier
							.semantics { contentDescription = knopf.kennung.ifEmpty { knopf.titel } }
							.then(if (knopf.haupt) Modifier.focusRequester(hauptFokus) else Modifier),
					) {
						Text(text = knopf.titel, fontSize = 18.sp, fontWeight = FontWeight.SemiBold)
					}
				}
			}
		}

		LaunchedEffect(meldung) {
			// erst nach dem Einblenden fokussieren, sonst geht der Fokus an die Fläche dahinter
			delay(150)
			runCatching { hauptFokus.requestFocus() }
		}
	}
}
