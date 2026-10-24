package org.jellyfin.androidtv.kinolel

import android.graphics.Bitmap
import android.graphics.Color
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.FilterQuality
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.zxing.BarcodeFormat
import com.google.zxing.EncodeHintType
import com.google.zxing.qrcode.QRCodeWriter
import com.google.zxing.qrcode.decoder.ErrorCorrectionLevel

/** QR-Code als Bild (schwarz auf weiß, ohne Rand – den Rand macht die weiße Fläche drumherum). */
fun qrBild(text: String, pixel: Int = 512): Bitmap {
	val matrix = QRCodeWriter().encode(
		text,
		BarcodeFormat.QR_CODE,
		pixel,
		pixel,
		mapOf(EncodeHintType.MARGIN to 0, EncodeHintType.ERROR_CORRECTION to ErrorCorrectionLevel.M),
	)
	val punkte = IntArray(matrix.width * matrix.height) { i ->
		if (matrix[i % matrix.width, i / matrix.width]) Color.BLACK else Color.WHITE
	}
	return Bitmap.createBitmap(punkte, matrix.width, matrix.height, Bitmap.Config.ARGB_8888)
}

/** QR-Code auf weißer, abgerundeter Fläche – gut lesbar fürs Handy, auch vom Sofa aus. */
@Composable
fun QrCode(text: String, groesse: Dp, modifier: Modifier = Modifier) {
	val bild = remember(text) { qrBild(text).asImageBitmap() }
	Box(
		modifier = modifier
			.clip(RoundedCornerShape(12.dp))
			.background(androidx.compose.ui.graphics.Color.White)
			.padding(groesse / 14)
	) {
		Image(
			bitmap = bild,
			contentDescription = null,
			filterQuality = FilterQuality.None,
			modifier = Modifier.size(groesse),
		)
	}
}

/** Quick Connect: QR-Code öffnet am Handy kinolel.de mit schon eingetragenem Code – dort nur noch „Bestätigen“. */
@Composable
fun KinoLelQuickConnectQr(code: String) {
	androidx.compose.foundation.layout.BoxWithConstraints(
		modifier = Modifier
			.fillMaxSize()
			.semantics { contentDescription = "kinolel.quickconnect.qr" },
	) {
		// so groß wie die Spalte erlaubt (Platz für die Zeile darunter lassen), höchstens 240 dp
		val seite = minOf(maxWidth - 28.dp, maxHeight - 90.dp, 240.dp)
		androidx.compose.foundation.layout.Column(horizontalAlignment = androidx.compose.ui.Alignment.CenterHorizontally) {
			QrCode(text = Marke.quickConnectAdresse(code), groesse = seite)
			androidx.compose.foundation.layout.Spacer(Modifier.size(10.dp))
			org.jellyfin.androidtv.ui.base.Text(
				text = androidx.compose.ui.res.stringResource(org.jellyfin.androidtv.R.string.kinolel_quickconnect_qr),
				color = KinoLelFarben.TextLeise,
				fontSize = 15.sp,
				lineHeight = 20.sp,
				textAlign = TextAlign.Center,
				modifier = Modifier.widthIn(max = seite + 28.dp),
			)
		}
	}
}
