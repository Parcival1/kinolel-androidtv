package org.jellyfin.androidtv.ui.base

import androidx.compose.runtime.Immutable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color
import org.jellyfin.design.Tokens

// KinoLel: Farben wie kinolel.de – dunkles Blau (#0B0F18/#151B2A), Fokus deutlich in Lavendel (#9AA4FF),
// aktive Knöpfe in Indigo (#6C72EE). Mit der Fernbedienung ist der Fokus die einzige Orientierung.
fun colorScheme(): ColorScheme = ColorScheme(
	background = Color(0xFF0B0F18),
	onBackground = Color(0xFFF1F2FA),
	button = Color(0xCC1E2438),
	onButton = Color(0xFFDDE1F5),
	buttonFocused = Color(0xFF9AA4FF),
	onButtonFocused = Color(0xFF0B0F18),
	buttonDisabled = Color(0x331E2438),
	onButtonDisabled = Color(0xFF6B7088),
	buttonActive = Color(0x996C72EE),
	onButtonActive = Color(0xFFFFFFFF),
	input = Color(0xCC1E2438),
	onInput = Color(0xFFDDE1F5),
	inputFocused = Color(0xFF9AA4FF),
	onInputFocused = Color(0xFF0B0F18),
	rangeControlBackground = Tokens.Color.colorBluegrey700,
	rangeControlFill = Color(0xFF9AA4FF),
	rangeControlKnob = Tokens.Color.colorBluegrey100,
	seekbarBuffer = Tokens.Color.colorBluegrey300,
	recording = Tokens.Color.colorRed300,
	onRecording = Tokens.Color.colorRed25,
	badge = Color(0xFF6C72EE),
	onBadge = Tokens.Color.colorBluegrey100,
	listHeader = Tokens.Color.colorGrey50,
	listOverline = Tokens.Color.colorGrey500,
	listHeadline = Tokens.Color.colorGrey25,
	listCaption = Tokens.Color.colorGrey200,
	listButton = Color.Transparent,
	listButtonFocused = Color(0xFF2E3560),
	surface = Color(0xFF151B2A),
	scrim = Tokens.Color.colorBlack.copy(alpha = 0.67f),
)

@Immutable
data class ColorScheme(
	val background: Color,
	val onBackground: Color,

	val button: Color,
	val onButton: Color,
	val buttonFocused: Color,
	val onButtonFocused: Color,
	val buttonDisabled: Color,
	val onButtonDisabled: Color,
	val buttonActive: Color,
	val onButtonActive: Color,

	val input: Color,
	val onInput: Color,
	val inputFocused: Color,
	val onInputFocused: Color,

	val rangeControlBackground: Color,
	val rangeControlFill: Color,
	val rangeControlKnob: Color,
	val seekbarBuffer: Color,

	val recording: Color,
	val onRecording: Color,

	val badge: Color,
	val onBadge: Color,

	val listHeader: Color,
	val listOverline: Color,
	val listHeadline: Color,
	val listCaption: Color,
	val listButton: Color,
	val listButtonFocused: Color,

	val surface: Color,
	val scrim: Color,
)

val LocalColorScheme = staticCompositionLocalOf { colorScheme() }
