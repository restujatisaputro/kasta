package id.kasta.app.inventory

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import id.kasta.app.data.remote.ProductDto
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import javax.inject.Inject

@HiltViewModel
class InventoryViewModel
    @Inject
    constructor(
        private val repository: InventoryRepository,
    ) : ViewModel() {
        private val mutableState = MutableStateFlow(InventoryUiState())
        val state: StateFlow<InventoryUiState> = mutableState.asStateFlow()

        init {
            refresh()
        }

        fun refresh() =
            launch {
                val current = mutableState.value
                val (products, summary) = repository.load(current.query, current.lowStockOnly)
                mutableState.value = current.copy(products = products, summary = summary, busy = false)
            }

        fun filters(
            query: String? = null,
            lowStock: Boolean? = null,
        ) {
            mutableState.value =
                mutableState.value.copy(
                    query = query ?: mutableState.value.query,
                    lowStockOnly = lowStock ?: mutableState.value.lowStockOnly,
                )
        }

        fun add() {
            mutableState.value = mutableState.value.copy(productForm = ProductForm(), editingProductId = null)
        }

        fun edit(product: ProductDto) {
            mutableState.value =
                mutableState.value.copy(
                    editingProductId = product.id,
                    productForm =
                        ProductForm(
                            product.sku,
                            product.barcode.orEmpty(),
                            product.name,
                            product.category,
                            product.unit,
                            product.purchasePrice,
                            product.salePrice,
                            product.openingStock,
                            product.minimumStock,
                            product.isActive,
                        ),
                )
        }

        fun updateProductForm(form: ProductForm) {
            mutableState.value = mutableState.value.copy(productForm = form, error = null)
        }

        fun saveProduct() {
            val current = mutableState.value
            val form = current.productForm ?: return
            if (form.sku.isBlank() || form.name.isBlank() || form.category.isBlank()) {
                mutableState.value = current.copy(error = "Isi SKU, nama, dan kategori produk.")
                return
            }
            launch {
                if (current.editingProductId == null) {
                    repository.create(form)
                } else {
                    repository.update(current.editingProductId, form)
                }
                mutableState.value =
                    mutableState.value.copy(
                        productForm = null,
                        editingProductId = null,
                        notice = "Produk berhasil disimpan.",
                    )
                refresh()
            }
        }

        fun closeProduct() {
            mutableState.value = mutableState.value.copy(productForm = null, error = null)
        }

        fun openMovement(product: ProductDto) {
            mutableState.value =
                mutableState.value.copy(
                    movementProduct = product,
                    movementForm = MovementForm(),
                )
        }

        fun updateMovement(form: MovementForm) {
            mutableState.value = mutableState.value.copy(movementForm = form, error = null)
        }

        fun saveMovement() {
            val current = mutableState.value
            val product = current.movementProduct ?: return
            if (current.movementForm.value.toBigDecimalOrNull() == null || current.movementForm.reason.length < 3) {
                mutableState.value = current.copy(error = "Isi jumlah dan alasan perubahan stok.")
                return
            }
            launch {
                repository.move(product.id, current.movementForm)
                mutableState.value =
                    mutableState.value.copy(
                        movementProduct = null,
                        notice = "Perubahan stok berhasil dicatat.",
                    )
                refresh()
            }
        }

        fun closeMovement() {
            mutableState.value = mutableState.value.copy(movementProduct = null, error = null)
        }

        fun openScanner() {
            mutableState.value = mutableState.value.copy(scannerOpen = true, error = null)
        }

        fun closeScanner() {
            mutableState.value = mutableState.value.copy(scannerOpen = false)
        }

        fun barcodeFound(value: String) {
            if (!mutableState.value.scannerOpen || mutableState.value.busy) return
            mutableState.value = mutableState.value.copy(scannerOpen = false)
            launch {
                val product = repository.byBarcode(value)
                mutableState.value =
                    mutableState.value.copy(
                        products = listOf(product),
                        notice = "${product.name} ditemukan.",
                    )
            }
        }

        private fun launch(block: suspend () -> Unit) {
            mutableState.value = mutableState.value.copy(busy = true, error = null)
            viewModelScope.launch {
                runCatching { block() }
                    .onFailure { error ->
                        mutableState.value =
                            mutableState.value.copy(
                                busy = false,
                                error = error.message ?: "Data inventori belum dapat diproses.",
                            )
                    }
            }
        }
    }
