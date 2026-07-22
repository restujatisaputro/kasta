package id.kasta.app.receiptscan

import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Matrix
import android.graphics.Paint
import androidx.exifinterface.media.ExifInterface
import java.io.File
import java.io.FileOutputStream
import kotlin.math.hypot
import kotlin.math.max
import kotlin.math.roundToInt

data class ProcessedReceiptImages(
    val original: File,
    val processed: File,
)

object ReceiptImageProcessor {
    private const val MAX_EDGE = 2200

    fun process(
        original: File,
        outputDirectory: File,
        quad: DocumentQuad,
    ): ProcessedReceiptImages {
        val decoded = decodeScaled(original)
        val oriented = orient(decoded, ExifInterface(original).rotationDegrees)
        if (oriented !== decoded) decoded.recycle()
        val cropped = perspectiveCrop(oriented, quad)
        if (cropped !== oriented) oriented.recycle()
        val enhanced = enhanceContrast(cropped)
        if (enhanced !== cropped) cropped.recycle()
        val output = File(outputDirectory, "nota-processed-${System.currentTimeMillis()}.jpg")
        FileOutputStream(output).use { stream ->
            check(enhanced.compress(Bitmap.CompressFormat.JPEG, 90, stream)) {
                "Gambar hasil tidak dapat disimpan"
            }
        }
        enhanced.recycle()
        return ProcessedReceiptImages(original, output)
    }

    private fun decodeScaled(file: File): Bitmap {
        val bounds = BitmapFactory.Options().apply { inJustDecodeBounds = true }
        BitmapFactory.decodeFile(file.absolutePath, bounds)
        var sample = 1
        while (max(bounds.outWidth, bounds.outHeight) / sample > MAX_EDGE) sample *= 2
        val options = BitmapFactory.Options().apply { inSampleSize = sample }
        return requireNotNull(BitmapFactory.decodeFile(file.absolutePath, options)) {
            "Foto nota tidak dapat dibaca"
        }
    }

    private fun orient(
        bitmap: Bitmap,
        rotation: Int,
    ): Bitmap {
        if (rotation == 0) return bitmap
        val matrix = Matrix().apply { postRotate(rotation.toFloat()) }
        return Bitmap.createBitmap(bitmap, 0, 0, bitmap.width, bitmap.height, matrix, true)
    }

    private fun perspectiveCrop(
        bitmap: Bitmap,
        requested: DocumentQuad,
    ): Bitmap {
        val quad = if (requested.isUsable()) requested else DocumentQuad()
        val source =
            floatArrayOf(
                quad.topLeftX * bitmap.width,
                quad.topLeftY * bitmap.height,
                quad.topRightX * bitmap.width,
                quad.topRightY * bitmap.height,
                quad.bottomRightX * bitmap.width,
                quad.bottomRightY * bitmap.height,
                quad.bottomLeftX * bitmap.width,
                quad.bottomLeftY * bitmap.height,
            )
        val targetWidth =
            max(
                distance(source[0], source[1], source[2], source[3]),
                distance(source[6], source[7], source[4], source[5]),
            ).roundToInt().coerceIn(320, MAX_EDGE)
        val targetHeight =
            max(
                distance(source[0], source[1], source[6], source[7]),
                distance(source[2], source[3], source[4], source[5]),
            ).roundToInt().coerceIn(320, MAX_EDGE)
        val destination =
            floatArrayOf(
                0f,
                0f,
                targetWidth.toFloat(),
                0f,
                targetWidth.toFloat(),
                targetHeight.toFloat(),
                0f,
                targetHeight.toFloat(),
            )
        val matrix = Matrix()
        if (!matrix.setPolyToPoly(source, 0, destination, 0, 4)) return bitmap
        return Bitmap.createBitmap(targetWidth, targetHeight, Bitmap.Config.ARGB_8888).also {
            Canvas(it).drawBitmap(bitmap, matrix, Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG))
        }
    }

    private fun enhanceContrast(source: Bitmap): Bitmap {
        val width = source.width
        val height = source.height
        val pixels = IntArray(width * height)
        source.getPixels(pixels, 0, width, 0, 0, width, height)
        val histogram = IntArray(256)
        pixels.forEach { pixel ->
            val gray = (Color.red(pixel) * 30 + Color.green(pixel) * 59 + Color.blue(pixel) * 11) / 100
            histogram[gray]++
        }
        val low = percentile(histogram, pixels.size, 0.02f)
        val high = percentile(histogram, pixels.size, 0.98f).coerceAtLeast(low + 1)
        for (index in pixels.indices) {
            val pixel = pixels[index]
            val gray = (Color.red(pixel) * 30 + Color.green(pixel) * 59 + Color.blue(pixel) * 11) / 100
            val stretched = ((gray - low) * 255 / (high - low)).coerceIn(0, 255)
            pixels[index] = Color.rgb(stretched, stretched, stretched)
        }
        return Bitmap.createBitmap(pixels, width, height, Bitmap.Config.ARGB_8888)
    }

    private fun percentile(
        histogram: IntArray,
        count: Int,
        fraction: Float,
    ): Int {
        val target = (count * fraction).roundToInt()
        var cumulative = 0
        histogram.forEachIndexed { value, frequency ->
            cumulative += frequency
            if (cumulative >= target) return value
        }
        return 255
    }

    private fun distance(
        x1: Float,
        y1: Float,
        x2: Float,
        y2: Float,
    ): Float = hypot(x2 - x1, y2 - y1)
}
