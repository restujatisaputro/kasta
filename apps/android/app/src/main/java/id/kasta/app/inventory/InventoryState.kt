package id.kasta.app.inventory

import id.kasta.app.data.remote.InventorySummaryDto
import id.kasta.app.data.remote.ProductDto

data class ProductForm(
    val sku: String = "",
    val barcode: String = "",
    val name: String = "",
    val category: String = "",
    val unit: String = "PCS",
    val purchasePrice: String = "0.00",
    val salePrice: String = "0.00",
    val openingStock: String = "0.000",
    val minimumStock: String = "0.000",
    val isActive: Boolean = true,
)

data class MovementForm(
    val type: String = "STOCK_IN",
    val value: String = "",
    val reason: String = "",
    val reference: String = "",
)

data class InventoryUiState(
    val products: List<ProductDto> = emptyList(),
    val summary: InventorySummaryDto? = null,
    val query: String = "",
    val lowStockOnly: Boolean = false,
    val productForm: ProductForm? = null,
    val editingProductId: String? = null,
    val movementProduct: ProductDto? = null,
    val movementForm: MovementForm = MovementForm(),
    val scannerOpen: Boolean = false,
    val busy: Boolean = false,
    val error: String? = null,
    val notice: String? = null,
)
