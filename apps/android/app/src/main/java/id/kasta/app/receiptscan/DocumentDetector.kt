package id.kasta.app.receiptscan

import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import kotlin.math.max

class DocumentDetector(
    private val onDetected: (DocumentQuad, Boolean) -> Unit,
) : ImageAnalysis.Analyzer {
    override fun analyze(image: ImageProxy) {
        try {
            val plane = image.planes.firstOrNull()
            if (plane == null) {
                onDetected(DocumentQuad(), false)
                return
            }
            val width = image.width
            val height = image.height
            val buffer = plane.buffer
            val rowStride = plane.rowStride
            val pixelStride = plane.pixelStride
            val step = max(4, minOf(width, height) / 90)
            var luminanceTotal = 0L
            var sampleCount = 0
            for (y in 0 until height step step) {
                for (x in 0 until width step step) {
                    luminanceTotal += buffer.get(y * rowStride + x * pixelStride).toInt() and 0xff
                    sampleCount++
                }
            }
            val mean = if (sampleCount == 0) 128 else (luminanceTotal / sampleCount).toInt()
            var minX = width
            var minY = height
            var maxX = 0
            var maxY = 0
            var brightCount = 0
            val brightRows = mutableListOf<BrightRow>()
            val threshold = (mean + 16).coerceAtMost(225)
            for (y in 0 until height step step) {
                var rowMinX = width
                var rowMaxX = 0
                for (x in 0 until width step step) {
                    val value = buffer.get(y * rowStride + x * pixelStride).toInt() and 0xff
                    if (value >= threshold) {
                        minX = minOf(minX, x)
                        minY = minOf(minY, y)
                        maxX = maxOf(maxX, x)
                        maxY = maxOf(maxY, y)
                        rowMinX = minOf(rowMinX, x)
                        rowMaxX = maxOf(rowMaxX, x)
                        brightCount++
                    }
                }
                if (rowMaxX > rowMinX) brightRows += BrightRow(y, rowMinX, rowMaxX)
            }
            val detected =
                brightCount > sampleCount / 12 &&
                    maxX - minX > width * 0.35f &&
                    maxY - minY > height * 0.35f
            val rawQuad =
                if (detected) {
                    val bandHeight = ((maxY - minY) * 0.2f).toInt().coerceAtLeast(step)
                    val topRows = brightRows.filter { it.y <= minY + bandHeight }
                    val bottomRows = brightRows.filter { it.y >= maxY - bandHeight }
                    DocumentQuad(
                        topLeftX = topRows.averageLeft(minX).toFloat() / width,
                        topLeftY = minY.toFloat() / height,
                        topRightX = topRows.averageRight(maxX).toFloat() / width,
                        topRightY = minY.toFloat() / height,
                        bottomRightX = bottomRows.averageRight(maxX).toFloat() / width,
                        bottomRightY = maxY.toFloat() / height,
                        bottomLeftX = bottomRows.averageLeft(minX).toFloat() / width,
                        bottomLeftY = maxY.toFloat() / height,
                    )
                } else {
                    DocumentQuad()
                }
            val quad = rotateAndOrder(rawQuad, image.imageInfo.rotationDegrees)
            onDetected(quad, detected && quad.isUsable())
        } finally {
            image.close()
        }
    }
}

private data class BrightRow(
    val y: Int,
    val left: Int,
    val right: Int,
)

private data class NormalizedPoint(
    val x: Float,
    val y: Float,
)

private fun List<BrightRow>.averageLeft(fallback: Int): Int {
    return if (isEmpty()) fallback else sumOf(BrightRow::left) / size
}

private fun List<BrightRow>.averageRight(fallback: Int): Int {
    return if (isEmpty()) fallback else sumOf(BrightRow::right) / size
}

private fun rotateAndOrder(
    quad: DocumentQuad,
    rotation: Int,
): DocumentQuad {
    val points =
        listOf(
            NormalizedPoint(quad.topLeftX, quad.topLeftY),
            NormalizedPoint(quad.topRightX, quad.topRightY),
            NormalizedPoint(quad.bottomRightX, quad.bottomRightY),
            NormalizedPoint(quad.bottomLeftX, quad.bottomLeftY),
        ).map { point ->
            when (rotation) {
                90 -> NormalizedPoint(1f - point.y, point.x)
                180 -> NormalizedPoint(1f - point.x, 1f - point.y)
                270 -> NormalizedPoint(point.y, 1f - point.x)
                else -> point
            }
        }.sortedBy(NormalizedPoint::y)
    val top = points.take(2).sortedBy(NormalizedPoint::x)
    val bottom = points.takeLast(2).sortedBy(NormalizedPoint::x)
    return DocumentQuad(
        topLeftX = top[0].x,
        topLeftY = top[0].y,
        topRightX = top[1].x,
        topRightY = top[1].y,
        bottomRightX = bottom[1].x,
        bottomRightY = bottom[1].y,
        bottomLeftX = bottom[0].x,
        bottomLeftY = bottom[0].y,
    )
}
