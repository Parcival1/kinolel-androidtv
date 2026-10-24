package org.jellyfin.androidtv.kinolel

import android.os.Bundle
import android.view.LayoutInflater
import android.view.ViewGroup
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.fragment.app.Fragment
import androidx.fragment.compose.content
import kotlinx.coroutines.delay
import org.jellyfin.androidtv.R
import org.jellyfin.androidtv.ui.base.Text
import org.jellyfin.androidtv.ui.base.button.Button
import org.jellyfin.androidtv.ui.startup.StartupActivity

/** KinoLel: kinolel.de beim ersten Start nicht erreichbar – verständlicher Hinweis, neuer Versuch per OK oder von selbst. */
class KinoLelKeineVerbindungFragment : Fragment() {
	private fun erneut() = (activity as? StartupActivity)?.kinolelServerAnlegen()

	override fun onCreateView(inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?) = content {
		val knopf = remember { FocusRequester() }

		LaunchedEffect(Unit) {
			runCatching { knopf.requestFocus() }
			delay(15_000)
			erneut()
		}

		Column(
			verticalArrangement = Arrangement.spacedBy(24.dp, Alignment.CenterVertically),
			horizontalAlignment = Alignment.CenterHorizontally,
			modifier = Modifier.fillMaxSize(),
		) {
			Image(
				painter = painterResource(R.drawable.app_logo),
				contentDescription = stringResource(R.string.app_name),
				modifier = Modifier.width(320.dp),
			)
			Text(
				text = stringResource(R.string.kinolel_keine_verbindung),
				color = KinoLelFarben.Text,
				fontSize = 22.sp,
				lineHeight = 32.sp,
				textAlign = TextAlign.Center,
				modifier = Modifier.widthIn(max = 640.dp),
			)
			Button(
				onClick = { erneut() },
				modifier = Modifier
					.focusRequester(knopf)
					.semantics { contentDescription = "kinolel.verbindung.erneut" },
			) {
				Text(stringResource(R.string.kinolel_erneut_versuchen), fontSize = 18.sp)
			}
		}
	}
}
