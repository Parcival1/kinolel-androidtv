package org.jellyfin.androidtv.ui.composable.compat

import android.content.Context
import android.view.View
import androidx.activity.compose.BackHandler
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.lifecycle.withStarted
import kotlinx.coroutines.flow.distinctUntilChanged
import kotlinx.coroutines.flow.map
import org.jellyfin.androidtv.ui.browsing.DestinationFragmentView
import org.jellyfin.androidtv.ui.navigation.NavigationAction
import org.jellyfin.androidtv.ui.navigation.NavigationRepository
import org.koin.compose.koinInject

@Composable
fun AppNavigationHost(
	modifier: Modifier = Modifier,
	navigationRepository: NavigationRepository = koinInject(),
) {
	val factory = remember { AppNavigationHostViewFactory() }

	val canGoBack by remember {
		navigationRepository.currentAction.map { navigationRepository.canGoBack }.distinctUntilChanged()
	}.collectAsState(navigationRepository.canGoBack)

	BackHandler(canGoBack) { navigationRepository.goBack() }

	AndroidView(
		factory = factory,
		modifier = modifier,
	)

	val lifecycle = LocalLifecycleOwner.current.lifecycle
	LaunchedEffect(Unit) {
		navigationRepository.currentAction.collect { action ->
			// KinoLel (Lel 24.10.: nach dem Wiederöffnen „nur Hintergrund, keine Inhalte“): erst umschalten, wenn die
			// Activity wieder sichtbar ist. Sonst baut sich die Startseite auf, während sie im Hintergrund gestoppt ist
			// (Wiederöffnen über die StartupActivity setzt die Navigation zurück), und ihre Reihen fehlen danach.
			lifecycle.withStarted {
				when (action) {
					is NavigationAction.NavigateFragment -> factory.view.navigate(action)
					NavigationAction.GoBack -> factory.view.goBack()
					NavigationAction.Nothing -> Unit
				}
			}
		}
	}
}

private class AppNavigationHostViewFactory : (Context) -> View {
	private var _view: DestinationFragmentView? = null

	val view get() = requireNotNull(_view)

	override operator fun invoke(
		context: Context
	): View = DestinationFragmentView(context).also { view ->
		_view = view
	}
}
