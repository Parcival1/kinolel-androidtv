package org.jellyfin.androidtv.ui.startup.fragment

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.compose.ui.platform.ComposeView
import androidx.compose.ui.platform.ViewCompositionStrategy
import androidx.fragment.app.Fragment
import androidx.fragment.app.commit
import androidx.fragment.app.replace
import org.jellyfin.androidtv.R
import org.jellyfin.androidtv.kinolel.KinoLelSeiteFragment
import org.jellyfin.androidtv.util.createBundle
import org.jellyfin.androidtv.ui.shared.toolbar.StartupToolbar

class StartupToolbarFragment : Fragment() {
	override fun onCreateView(
		inflater: LayoutInflater,
		container: ViewGroup?,
		savedInstanceState: Bundle?
	): View = ComposeView(requireContext()).apply {
		setViewCompositionStrategy(ViewCompositionStrategy.DisposeOnViewTreeLifecycleDestroyed)
		setContent {
			StartupToolbar(
				// KinoLel: eigene Hilfe (Bedienung, Quick Connect, QR-Code zur Hilfeseite) statt Jellyfin-Doku
				openHelp = {
					parentFragmentManager.commit {
						addToBackStack(null)
						replace<KinoLelSeiteFragment>(
							R.id.content_view, null, createBundle {
								putString(KinoLelSeiteFragment.ARG_SEITE, KinoLelSeiteFragment.HILFE)
								putBoolean(KinoLelSeiteFragment.ARG_OHNE_KOPF, true)
							}
						)
					}
				}
			)
		}
	}
}
