package id.kasta.app.inventory

import id.kasta.app.data.remote.InventoryApi
import id.kasta.app.data.remote.InventorySummaryDto
import id.kasta.app.data.remote.ProductCreateDto
import id.kasta.app.data.remote.ProductDto
import id.kasta.app.data.remote.ProductUpdateDto
import id.kasta.app.data.remote.StockMovementDto
import id.kasta.app.data.session.SessionStore
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class InventoryRepository
    @Inject
    constructor(
        private val api: InventoryApi,
        private val sessionStore: SessionStore,
    ) {
        private fun session() = requireNotNull(sessionStore.get()) { "Sesi sudah berakhir." }

        suspend fun load(
            query: String = "",
            lowStock: Boolean = false,
        ): Pair<List<ProductDto>, InventorySummaryDto> {
            val session = session()
            val authorization = "Bearer ${session.accessToken}"
            return api.products(session.businessId, authorization, query.ifBlank { null }, lowStock).items to
                api.summary(session.businessId, authorization)
        }

        suspend fun byBarcode(barcode: String): ProductDto {
            val session = session()
            return api.byBarcode(session.businessId, barcode, "Bearer ${session.accessToken}")
        }

        suspend fun create(form: ProductForm): ProductDto {
            val session = session()
            return api.create(
                session.businessId,
                "Bearer ${session.accessToken}",
                ProductCreateDto(
                    form.sku,
                    form.barcode.ifBlank { null },
                    form.name,
                    form.category,
                    form.unit,
                    form.purchasePrice,
                    form.salePrice,
                    form.openingStock,
                    form.minimumStock,
                    form.isActive,
                ),
            )
        }

        suspend fun update(
            productId: String,
            form: ProductForm,
        ): ProductDto {
            val session = session()
            return api.update(
                session.businessId,
                productId,
                "Bearer ${session.accessToken}",
                ProductUpdateDto(
                    form.sku,
                    form.barcode.ifBlank { null },
                    form.name,
                    form.category,
                    form.unit,
                    form.purchasePrice,
                    form.salePrice,
                    form.minimumStock,
                    form.isActive,
                ),
            )
        }

        suspend fun move(
            productId: String,
            form: MovementForm,
        ) {
            val session = session()
            api.move(
                session.businessId,
                productId,
                "Bearer ${session.accessToken}",
                StockMovementDto(
                    movementType = form.type,
                    quantity = form.value.takeUnless { form.type == "ADJUSTMENT" },
                    targetStock = form.value.takeIf { form.type == "ADJUSTMENT" },
                    reason = form.reason,
                    reference = form.reference,
                ),
            )
        }
    }
