package id.kasta.app.receiptscan

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageCapture
import androidx.camera.core.ImageCaptureException
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.camera.view.PreviewView
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.compose.LocalLifecycleOwner
import id.kasta.app.transactions.DEFAULT_EXPENSE_CATEGORIES
import id.kasta.app.transactions.INCOME_SOURCES
import id.kasta.app.transactions.PAYMENT_METHODS
import id.kasta.app.transactions.formatRupiah
import java.io.File
import java.math.BigDecimal
import java.util.concurrent.Executors

@Composable
fun ReceiptScanScreen(
    state: ReceiptScanUiState,
    onClose: () -> Unit,
    onDetected: (DocumentQuad, Boolean) -> Unit,
    onCaptured: (File) -> Unit,
    onRetry: () -> Unit,
    onFieldChange: (String, String) -> Unit,
    onChoicesChange: (String?, String?, String?, Boolean?) -> Unit,
    onConfirm: () -> Unit,
    onDone: () -> Unit,
) {
    when (state.stage) {
        ReceiptScanStage.CAMERA ->
            ReceiptCamera(
                state = state,
                onClose = onClose,
                onDetected = onDetected,
                onCaptured = onCaptured,
            )
        ReceiptScanStage.PROCESSING -> ProcessingReceipt(onClose)
        ReceiptScanStage.REVIEW ->
            ReceiptReview(
                state,
                onClose,
                onFieldChange,
                onChoicesChange,
                onConfirm,
            )
        ReceiptScanStage.CONFIRMED -> ConfirmationComplete(state.message, onDone)
        ReceiptScanStage.FAILED -> FailedReceipt(state.error, onRetry, onClose)
        ReceiptScanStage.CLOSED -> Unit
    }
}

@Composable
private fun ReceiptCamera(
    state: ReceiptScanUiState,
    onClose: () -> Unit,
    onDetected: (DocumentQuad, Boolean) -> Unit,
    onCaptured: (File) -> Unit,
) {
    val context = LocalContext.current
    var permissionGranted by remember {
        mutableStateOf(
            ContextCompat.checkSelfPermission(context, Manifest.permission.CAMERA) ==
                PackageManager.PERMISSION_GRANTED,
        )
    }
    val permissionLauncher =
        rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {
            permissionGranted = it
        }
    LaunchedEffect(Unit) {
        if (!permissionGranted) permissionLauncher.launch(Manifest.permission.CAMERA)
    }
    if (!permissionGranted) {
        CenteredMessage(
            title = "Izinkan kamera",
            detail = "KASTA memerlukan kamera untuk memotret nota. Foto hanya dikirim setelah Anda mengambilnya.",
            primaryLabel = "Minta izin",
            onPrimary = { permissionLauncher.launch(Manifest.permission.CAMERA) },
            onClose = onClose,
        )
        return
    }
    val imageCapture = remember { ImageCapture.Builder().build() }
    Box(Modifier.fillMaxSize()) {
        CameraPreview(
            imageCapture = imageCapture,
            onDetected = onDetected,
            modifier = Modifier.fillMaxSize(),
        )
        DocumentOverlay(state.quad, state.documentDetected, Modifier.fillMaxSize())
        Surface(
            color = Color.Black.copy(alpha = 0.58f),
            modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter),
        ) {
            Row(
                Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Column {
                    Text("Foto Nota", color = Color.White, fontWeight = FontWeight.Black)
                    Text(
                        if (state.documentDetected) "Nota terdeteksi — tahan sebentar" else "Arahkan seluruh nota ke bingkai",
                        color = if (state.documentDetected) Color(0xFF86EFAC) else Color.White,
                    )
                }
                TextButton(onClick = onClose) { Text("Tutup", color = Color.White) }
            }
        }
        Button(
            onClick = {
                val photo = File(context.cacheDir, "nota-original-${System.currentTimeMillis()}.jpg")
                imageCapture.takePicture(
                    ImageCapture.OutputFileOptions.Builder(photo).build(),
                    ContextCompat.getMainExecutor(context),
                    object : ImageCapture.OnImageSavedCallback {
                        override fun onImageSaved(output: ImageCapture.OutputFileResults) {
                            onCaptured(photo)
                        }

                        override fun onError(exception: ImageCaptureException) = Unit
                    },
                )
            },
            modifier =
                Modifier.align(Alignment.BottomCenter).padding(28.dp).testTag("receipt-shutter"),
        ) {
            Text(if (state.documentDetected) "Ambil Foto" else "Ambil secara manual")
        }
    }
}

@Composable
private fun CameraPreview(
    imageCapture: ImageCapture,
    onDetected: (DocumentQuad, Boolean) -> Unit,
    modifier: Modifier,
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val currentDetected by rememberUpdatedState(onDetected)
    val previewView = remember { PreviewView(context).apply { scaleType = PreviewView.ScaleType.FILL_CENTER } }
    val analysisExecutor = remember { Executors.newSingleThreadExecutor() }
    DisposableEffect(lifecycleOwner) {
        val future = ProcessCameraProvider.getInstance(context)
        var provider: ProcessCameraProvider? = null
        future.addListener(
            {
                provider = future.get()
                val preview = Preview.Builder().build().also { it.surfaceProvider = previewView.surfaceProvider }
                val analysis =
                    ImageAnalysis.Builder()
                        .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                        .build()
                        .also {
                            it.setAnalyzer(
                                analysisExecutor,
                                DocumentDetector { quad, detected ->
                                    previewView.post { currentDetected(quad, detected) }
                                },
                            )
                        }
                runCatching {
                    provider?.unbindAll()
                    provider?.bindToLifecycle(
                        lifecycleOwner,
                        CameraSelector.DEFAULT_BACK_CAMERA,
                        preview,
                        imageCapture,
                        analysis,
                    )
                }
            },
            ContextCompat.getMainExecutor(context),
        )
        onDispose {
            provider?.unbindAll()
            analysisExecutor.shutdown()
        }
    }
    AndroidView(factory = { previewView }, modifier = modifier)
}

@Composable
private fun DocumentOverlay(
    quad: DocumentQuad,
    detected: Boolean,
    modifier: Modifier,
) {
    Canvas(modifier) {
        val path = Path()
        path.moveTo(quad.topLeftX * size.width, quad.topLeftY * size.height)
        path.lineTo(quad.topRightX * size.width, quad.topRightY * size.height)
        path.lineTo(quad.bottomRightX * size.width, quad.bottomRightY * size.height)
        path.lineTo(quad.bottomLeftX * size.width, quad.bottomLeftY * size.height)
        path.close()
        drawPath(
            path,
            color = if (detected) Color(0xFF4ADE80) else Color.White,
            style = Stroke(width = if (detected) 8f else 5f),
        )
        if (detected) {
            drawCircle(Color(0xFF4ADE80), 9f, Offset(quad.topLeftX * size.width, quad.topLeftY * size.height))
        }
    }
}

@Composable
private fun ProcessingReceipt(onClose: () -> Unit) {
    Column(
        Modifier.fillMaxSize().padding(28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        CircularProgressIndicator()
        Text(
            "Merapikan dan membaca nota…",
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.Black,
            modifier = Modifier.padding(top = 20.dp),
        )
        Text("KASTA sedang memotong gambar, memperjelas tulisan, dan mencari jumlah pembayaran.")
        TextButton(onClick = onClose, modifier = Modifier.padding(top = 12.dp)) { Text("Batal") }
    }
}

@Composable
private fun ReceiptReview(
    state: ReceiptScanUiState,
    onClose: () -> Unit,
    onFieldChange: (String, String) -> Unit,
    onChoicesChange: (String?, String?, String?, Boolean?) -> Unit,
    onConfirm: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp),
    ) {
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Column {
                Text("Periksa Foto Nota", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
                Text("Transaksi belum dibuat")
            }
            TextButton(onClick = onClose) { Text("Tutup") }
        }
        state.error?.let { Notice(it, true) }
        if (state.duplicates.isNotEmpty()) {
            Notice(
                "Ada ${state.duplicates.size} nota mirip berdasarkan gambar, tanggal, total, nama toko, atau nomor nota.",
                true,
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(
                    checked = state.acknowledgeDuplicate,
                    onCheckedChange = { onChoicesChange(null, null, null, it) },
                )
                Text("Saya sudah memeriksa dan tetap ingin mencatat nota ini")
            }
        }
        FieldEditor(state, "merchant_name", "Nama toko", onFieldChange)
        FieldEditor(state, "receipt_date", "Tanggal (YYYY-MM-DD)", onFieldChange)
        FieldEditor(state, "receipt_number", "Nomor nota (opsional)", onFieldChange)
        FieldEditor(state, "subtotal", "Subtotal (opsional)", onFieldChange)
        FieldEditor(state, "discount", "Diskon (opsional)", onFieldChange)
        FieldEditor(state, "tax", "Pajak / PPN (opsional)", onFieldChange)
        FieldEditor(state, "total", "Total", onFieldChange)

        Text("Nota ini untuk", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 18.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            FilterChip(
                selected = state.entryKind == "EXPENSE",
                onClick = { onChoicesChange("EXPENSE", "PURCHASES", null, null) },
                label = { Text("Uang Keluar") },
            )
            FilterChip(
                selected = state.entryKind == "INCOME",
                onClick = { onChoicesChange("INCOME", "SALES", null, null) },
                label = { Text("Uang Masuk") },
            )
        }
        Text(
            if (state.entryKind == "INCOME") "Sumber pemasukan" else "Kategori pengeluaran",
            fontWeight = FontWeight.Bold,
            modifier = Modifier.padding(top = 12.dp),
        )
        val categories = if (state.entryKind == "INCOME") INCOME_SOURCES else DEFAULT_EXPENSE_CATEGORIES
        categories.forEach { (value, label) ->
            FilterChip(
                selected = state.categoryAccount == value,
                onClick = { onChoicesChange(null, value, null, null) },
                label = { Text(label) },
                modifier = Modifier.padding(end = 6.dp),
            )
        }
        Text("Metode pembayaran", fontWeight = FontWeight.Bold, modifier = Modifier.padding(top = 12.dp))
        PAYMENT_METHODS.forEach { (value, label) ->
            FilterChip(
                selected = state.paymentMethod == value,
                onClick = { onChoicesChange(null, null, value, null) },
                label = { Text(label) },
                modifier = Modifier.padding(end = 6.dp),
            )
        }
        if (state.items.isNotEmpty()) {
            Text(
                "Barang yang terbaca",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Black,
                modifier = Modifier.padding(top = 18.dp),
            )
            state.items.forEach { item ->
                Row(Modifier.fillMaxWidth().padding(vertical = 4.dp), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text(item.description, modifier = Modifier.weight(1f))
                    Text(rupiahFromDecimal(item.lineTotal), fontWeight = FontWeight.Bold)
                }
            }
        }
        Notice("KASTA hanya membuat transaksi setelah Anda menekan tombol konfirmasi.", false)
        Button(
            onClick = onConfirm,
            enabled = !state.busy,
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp).testTag("receipt-confirm"),
        ) {
            if (state.busy) CircularProgressIndicator(modifier = Modifier.height(20.dp)) else Text("Konfirmasi dan Buat Transaksi")
        }
        Spacer(Modifier.height(32.dp))
    }
}

@Composable
private fun FieldEditor(
    state: ReceiptScanUiState,
    name: String,
    label: String,
    onChange: (String, String) -> Unit,
) {
    val field = state.fields[name]
    OutlinedTextField(
        value = field?.value.orEmpty(),
        onValueChange = { onChange(name, it) },
        label = { Text(label) },
        supportingText = {
            val confidence = ((field?.confidence ?: 0f) * 100).toInt()
            Text(if (confidence >= 80) "Terbaca jelas ($confidence%)" else "Perlu diperiksa ($confidence%)")
        },
        singleLine = true,
        modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
    )
}

@Composable
private fun ConfirmationComplete(
    message: String?,
    onDone: () -> Unit,
) {
    CenteredMessage(
        title = "Nota sudah dicatat",
        detail = message ?: "Transaksi berhasil dibuat.",
        primaryLabel = "Kembali ke transaksi",
        onPrimary = onDone,
        onClose = onDone,
    )
}

@Composable
private fun FailedReceipt(
    error: String?,
    onRetry: () -> Unit,
    onClose: () -> Unit,
) {
    CenteredMessage(
        title = "Foto belum selesai diproses",
        detail = error ?: "Periksa koneksi atau ambil foto dengan cahaya yang lebih baik.",
        primaryLabel = "Coba lagi",
        onPrimary = onRetry,
        onClose = onClose,
    )
}

@Composable
private fun CenteredMessage(
    title: String,
    detail: String,
    primaryLabel: String,
    onPrimary: () -> Unit,
    onClose: () -> Unit,
) {
    Column(
        Modifier.fillMaxSize().padding(28.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Black)
        Text(detail, modifier = Modifier.padding(top = 10.dp))
        Button(onClick = onPrimary, modifier = Modifier.fillMaxWidth().padding(top = 22.dp)) {
            Text(primaryLabel)
        }
        OutlinedButton(onClick = onClose, modifier = Modifier.fillMaxWidth().padding(top = 8.dp)) {
            Text("Tutup")
        }
    }
}

@Composable
private fun Notice(
    text: String,
    error: Boolean,
) {
    Card(
        colors =
            CardDefaults.cardColors(
                containerColor =
                    if (error) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.primaryContainer,
            ),
        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
    ) {
        Text(text, modifier = Modifier.padding(14.dp))
    }
}

private fun rupiahFromDecimal(raw: String): String = runCatching { formatRupiah(BigDecimal(raw).longValueExact()) }.getOrDefault("Rp $raw")
