package org.jellyfin.androidtv.kinolel

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.width
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.jellyfin.androidtv.R
import org.jellyfin.androidtv.ui.background.AppThemeBackground

/**
 * KinoLel (Lel 25.10.: „Wenn man die App öffnet sieht man kurz für eine halbe Sekunde irgendwelche komischen
 * Menüelemente … Der Ladescreen muss also noch verlängert werden.“): Das Startbild (KinoLel-Logo auf dem Hintergrund,
 * wie der Start-Bildschirm) bleibt über der Startseite, bis deren Reihen fertig geladen sind – nicht nach fester Zeit.
 * Notbremse: nach [NOTBREMSE_MS] verschwindet es trotzdem (z. B. Server langsam).
 */
object KinoLelStartseite {
	const val NOTBREMSE_MS = 20_000L
	const val PRUEFTAKT_MS = 100L

	private val _bereit = MutableStateFlow(false)
	val bereit: StateFlow<Boolean> = _bereit.asStateFlow()

	fun laedt() {
		_bereit.value = false
	}

	fun fertig() {
		_bereit.value = true
	}
}

@Composable
fun KinoLelLadebild() {
	val bereit by KinoLelStartseite.bereit.collectAsState()
	AnimatedVisibility(visible = !bereit, enter = androidx.compose.animation.EnterTransition.None, exit = fadeOut(tween(250))) {
		Box(
			modifier = Modifier.fillMaxSize(),
			contentAlignment = Alignment.Center,
		) {
			AppThemeBackground()
			Image(
				painter = painterResource(R.drawable.app_logo),
				contentDescription = stringResource(R.string.app_name),
				modifier = Modifier
					.width(400.dp)
					.fillMaxHeight(),
			)
		}
	}
}
