package id.kasta.app.inventory

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import id.kasta.app.data.remote.ProductDto
import id.kasta.app.transactions.formatRupiah

@Composable
fun InventoryScreen(
    state: InventoryUiState,
    onBack: () -> Unit,
    onRefresh: () -> Unit,
    onFilters: (String?, Boolean?) -> Unit,
    onAdd: () -> Unit,
    onEdit: (ProductDto) -> Unit,
    onProductForm: (ProductForm) -> Unit,
    onSaveProduct: () -> Unit,
    onCloseProduct: () -> Unit,
    onMovement: (ProductDto) -> Unit,
    onMovementForm: (MovementForm) -> Unit,
    onSaveMovement: () -> Unit,
    onCloseMovement: () -> Unit,
    onScan: () -> Unit,
) {
    Scaffold { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(20.dp),
        ) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("Produk dan stok", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Black)
                    Text("Pantau barang usaha dengan mudah")
                }
                TextButton(onClick = onBack) { Text("Kembali") }
            }
            state.notice?.let { Message(it, false) }
            state.error?.let { Message(it, true) }
            Spacer(Modifier.height(16.dp))
            state.summary?.let { summary ->
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    Metric("Nilai persediaan", formatMoney(summary.inventoryValue), Modifier.weight(1f))
                    Metric("Stok minimum", "${summary.lowStockCount} produk", Modifier.weight(1f))
                }
            }
            Spacer(Modifier.height(16.dp))
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(onClick = onAdd, modifier = Modifier.weight(1f)) { Text("Tambah produk") }
                OutlinedButton(onClick = onScan, modifier = Modifier.weight(1f)) { Text("Scan barcode") }
            }
            OutlinedTextField(
                value = state.query,
                onValueChange = { onFilters(it, null) },
                label = { Text("Cari nama, SKU, atau barcode") },
                modifier = Modifier.fillMaxWidth(),
                trailingIcon = { TextButton(onClick = onRefresh) { Text("Cari") } },
            )
            FilterChip(
                selected = state.lowStockOnly,
                onClick = {
                    onFilters(null, !state.lowStockOnly)
                    onRefresh()
                },
                label = { Text("Hanya stok minimum") },
            )
            state.products.forEach { product ->
                ProductCard(product, onEdit, onMovement)
            }
            if (state.products.isEmpty() && !state.busy) {
                Text("Belum ada produk.", modifier = Modifier.padding(vertical = 30.dp))
            }
        }
    }
    state.productForm?.let { form ->
        ProductDialog(
            form,
            editing = state.editingProductId != null,
            onChange = onProductForm,
            onSave = onSaveProduct,
            onClose = onCloseProduct,
            busy = state.busy,
        )
    }
    state.movementProduct?.let { product ->
        MovementDialog(
            product,
            state.movementForm,
            onMovementForm,
            onSaveMovement,
            onCloseMovement,
            state.busy,
        )
    }
}

@Composable
private fun ProductCard(
    product: ProductDto,
    onEdit: (ProductDto) -> Unit,
    onMovement: (ProductDto) -> Unit,
) {
    Card(
        Modifier.fillMaxWidth().padding(vertical = 6.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surfaceContainerLow),
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text(product.name, fontWeight = FontWeight.ExtraBold)
                    Text("${product.sku} · ${product.barcode ?: "Tanpa barcode"}")
                }
                Text(
                    if (product.isLowStock) "Perlu diisi" else "Aman",
                    color = if (product.isLowStock) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                    fontWeight = FontWeight.Bold,
                )
            }
            Text("Stok ${product.currentStock} ${product.unit}", style = MaterialTheme.typography.titleMedium)
            Text("Jual ${formatMoney(product.salePrice)} · Nilai ${formatMoney(product.inventoryValue)}")
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = { onMovement(product) }) { Text("Ubah stok") }
                TextButton(onClick = { onEdit(product) }) { Text("Edit") }
            }
        }
    }
}

@Composable
private fun ProductDialog(
    form: ProductForm,
    editing: Boolean,
    onChange: (ProductForm) -> Unit,
    onSave: () -> Unit,
    onClose: () -> Unit,
    busy: Boolean,
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text(if (editing) "Edit produk" else "Tambah produk") },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState())) {
                ProductField("Nama produk", form.name) { onChange(form.copy(name = it)) }
                ProductField("SKU", form.sku) { onChange(form.copy(sku = it)) }
                ProductField("Barcode", form.barcode) { onChange(form.copy(barcode = it)) }
                ProductField("Kategori", form.category) { onChange(form.copy(category = it)) }
                ProductField("Satuan", form.unit) { onChange(form.copy(unit = it.uppercase())) }
                ProductField("Harga beli", form.purchasePrice, true) { onChange(form.copy(purchasePrice = it)) }
                ProductField("Harga jual", form.salePrice, true) { onChange(form.copy(salePrice = it)) }
                if (!editing) ProductField("Stok awal", form.openingStock, true) { onChange(form.copy(openingStock = it)) }
                ProductField("Stok minimum", form.minimumStock, true) { onChange(form.copy(minimumStock = it)) }
                Row {
                    Checkbox(checked = form.isActive, onCheckedChange = { onChange(form.copy(isActive = it)) })
                    Text("Produk aktif", modifier = Modifier.padding(top = 12.dp))
                }
            }
        },
        confirmButton = { Button(onClick = onSave, enabled = !busy) { Text("Simpan") } },
        dismissButton = { TextButton(onClick = onClose) { Text("Batal") } },
    )
}

@Composable
private fun MovementDialog(
    product: ProductDto,
    form: MovementForm,
    onChange: (MovementForm) -> Unit,
    onSave: () -> Unit,
    onClose: () -> Unit,
    busy: Boolean,
) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("Ubah stok ${product.name}") },
        text = {
            Column {
                Text("Stok sekarang ${product.currentStock} ${product.unit}")
                listOf(
                    "STOCK_IN" to "Masuk",
                    "STOCK_OUT" to "Keluar",
                    "ADJUSTMENT" to "Penyesuaian",
                    "DAMAGED" to "Rusak",
                    "LOST" to "Hilang",
                ).forEach { (value, label) ->
                    FilterChip(
                        selected = form.type == value,
                        onClick = { onChange(form.copy(type = value)) },
                        label = { Text(label) },
                    )
                }
                ProductField(if (form.type == "ADJUSTMENT") "Stok hasil hitung" else "Jumlah", form.value, true) {
                    onChange(form.copy(value = it))
                }
                ProductField("Alasan", form.reason) { onChange(form.copy(reason = it)) }
                ProductField("Nomor referensi (opsional)", form.reference) { onChange(form.copy(reference = it)) }
            }
        },
        confirmButton = { Button(onClick = onSave, enabled = !busy) { Text("Catat") } },
        dismissButton = { TextButton(onClick = onClose) { Text("Batal") } },
    )
}

@Composable
private fun ProductField(
    label: String,
    value: String,
    numeric: Boolean = false,
    onChange: (String) -> Unit,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = if (numeric) KeyboardType.Decimal else KeyboardType.Text),
        modifier = Modifier.fillMaxWidth(),
    )
}

@Composable
private fun Metric(
    label: String,
    value: String,
    modifier: Modifier,
) {
    Card(modifier) {
        Column(Modifier.padding(14.dp)) {
            Text(label, style = MaterialTheme.typography.bodySmall)
            Text(value, fontWeight = FontWeight.Black)
        }
    }
}

@Composable
private fun Message(
    text: String,
    error: Boolean,
) {
    Text(
        text,
        color = if (error) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
        modifier = Modifier.padding(vertical = 8.dp),
    )
}

private fun formatMoney(value: String): String = formatRupiah(value.toBigDecimalOrNull()?.toLong() ?: 0L)
