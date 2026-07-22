package id.kasta.app.data.remote

import com.google.gson.annotations.SerializedName
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Header
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Path
import retrofit2.http.Query

data class ProductDto(
    val id: String,
    @SerializedName("business_id") val businessId: String,
    val sku: String,
    val barcode: String?,
    val name: String,
    val category: String,
    val unit: String,
    @SerializedName("purchase_price") val purchasePrice: String,
    @SerializedName("sale_price") val salePrice: String,
    @SerializedName("opening_stock") val openingStock: String,
    @SerializedName("current_stock") val currentStock: String,
    @SerializedName("minimum_stock") val minimumStock: String,
    @SerializedName("is_active") val isActive: Boolean,
    @SerializedName("is_low_stock") val isLowStock: Boolean,
    @SerializedName("inventory_value") val inventoryValue: String,
)

data class ProductListDto(
    val items: List<ProductDto>,
    val total: Int,
)

data class ProductCreateDto(
    val sku: String,
    val barcode: String?,
    val name: String,
    val category: String,
    val unit: String,
    @SerializedName("purchase_price") val purchasePrice: String,
    @SerializedName("sale_price") val salePrice: String,
    @SerializedName("opening_stock") val openingStock: String,
    @SerializedName("minimum_stock") val minimumStock: String,
    @SerializedName("is_active") val isActive: Boolean,
)

data class ProductUpdateDto(
    val sku: String,
    val barcode: String?,
    val name: String,
    val category: String,
    val unit: String,
    @SerializedName("purchase_price") val purchasePrice: String,
    @SerializedName("sale_price") val salePrice: String,
    @SerializedName("minimum_stock") val minimumStock: String,
    @SerializedName("is_active") val isActive: Boolean,
)

data class StockMovementDto(
    @SerializedName("movement_type") val movementType: String,
    val quantity: String? = null,
    @SerializedName("target_stock") val targetStock: String? = null,
    @SerializedName("unit_cost") val unitCost: String? = null,
    val reason: String,
    val reference: String = "",
)

data class BestSellerDto(
    @SerializedName("product_id") val productId: String,
    val name: String,
    val unit: String,
    @SerializedName("quantity_sold") val quantitySold: String,
)

data class InventorySummaryDto(
    @SerializedName("product_count") val productCount: Int,
    @SerializedName("active_product_count") val activeProductCount: Int,
    @SerializedName("low_stock_count") val lowStockCount: Int,
    @SerializedName("inventory_value") val inventoryValue: String,
    @SerializedName("best_sellers") val bestSellers: List<BestSellerDto>,
)

interface InventoryApi {
    @GET("businesses/{business_id}/inventory/products")
    suspend fun products(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Query("q") query: String? = null,
        @Query("low_stock") lowStock: Boolean = false,
    ): ProductListDto

    @GET("businesses/{business_id}/inventory/products/by-barcode/{barcode}")
    suspend fun byBarcode(
        @Path("business_id") businessId: String,
        @Path("barcode") barcode: String,
        @Header("Authorization") authorization: String,
    ): ProductDto

    @GET("businesses/{business_id}/inventory/summary")
    suspend fun summary(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
    ): InventorySummaryDto

    @POST("businesses/{business_id}/inventory/products")
    suspend fun create(
        @Path("business_id") businessId: String,
        @Header("Authorization") authorization: String,
        @Body product: ProductCreateDto,
    ): ProductDto

    @PUT("businesses/{business_id}/inventory/products/{product_id}")
    suspend fun update(
        @Path("business_id") businessId: String,
        @Path("product_id") productId: String,
        @Header("Authorization") authorization: String,
        @Body product: ProductUpdateDto,
    ): ProductDto

    @POST("businesses/{business_id}/inventory/products/{product_id}/movements")
    suspend fun move(
        @Path("business_id") businessId: String,
        @Path("product_id") productId: String,
        @Header("Authorization") authorization: String,
        @Body movement: StockMovementDto,
    )
}
