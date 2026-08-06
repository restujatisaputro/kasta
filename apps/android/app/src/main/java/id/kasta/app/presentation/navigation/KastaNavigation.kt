package id.kasta.app.presentation.navigation

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ReceiptLong
import androidx.compose.material.icons.rounded.Assessment
import androidx.compose.material.icons.rounded.CameraAlt
import androidx.compose.material.icons.rounded.Home
import androidx.compose.material.icons.rounded.Menu
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.navigation
import androidx.navigation.compose.rememberNavController
import id.kasta.app.inventory.BarcodeScannerScreen
import id.kasta.app.inventory.InventoryScreen
import id.kasta.app.inventory.InventoryViewModel
import id.kasta.app.mentoraccess.MentorAccessScreen
import id.kasta.app.mentoraccess.MentorAccessViewModel
import id.kasta.app.notifications.NotificationScreen
import id.kasta.app.notifications.NotificationViewModel
import id.kasta.app.obligations.ObligationScreen
import id.kasta.app.obligations.ObligationViewModel
import id.kasta.app.onboarding.OnboardingScreen
import id.kasta.app.onboarding.OnboardingViewModel
import id.kasta.app.presentation.auth.AuthViewModel
import id.kasta.app.presentation.auth.BusinessSelectionScreen
import id.kasta.app.presentation.auth.LoginScreen
import id.kasta.app.presentation.auth.RegistrationScreen
import id.kasta.app.presentation.auth.SplashScreen
import id.kasta.app.presentation.home.HomeScreen
import id.kasta.app.presentation.home.HomeViewModel
import id.kasta.app.presentation.more.ConflictResolutionScreen
import id.kasta.app.presentation.more.MoreScreen
import id.kasta.app.presentation.more.OcrConfirmationScreen
import id.kasta.app.presentation.more.ProfileScreen
import id.kasta.app.presentation.more.SettingsScreen
import id.kasta.app.presentation.settings.SettingsViewModel
import id.kasta.app.receiptscan.ReceiptScanScreen
import id.kasta.app.receiptscan.ReceiptScanViewModel
import id.kasta.app.reports.ReportScreen
import id.kasta.app.reports.ReportViewModel
import id.kasta.app.transactions.SyncStatusScreen
import id.kasta.app.transactions.TransactionScreen
import id.kasta.app.transactions.TransactionViewModel

object KastaRoute {
    val Splash = "splash"
    val Login = "login"
    val BusinessSelection = "business-selection"
    val Registration = "registration"
    val Onboarding = "onboarding"
    val Main = "main"
    val Home = "home"
    val Transactions = "transactions"
    val Income = "income"
    val Expense = "expense"
    val Receipt = "receipt-camera"
    val OcrConfirmation = "receipt-confirmation"
    val Reports = "reports"
    val More = "more"
    val Products = "products"
    val Stock = "stock"
    val Payables = "payables"
    val Receivables = "receivables"
    val Mentor = "mentor"
    val Profile = "profile"
    val Settings = "settings"
    val Sync = "sync"
    val Conflicts = "conflicts"
    val Notifications = "notifications"
}

private data class BottomDestination(
    val route: String,
    val label: String,
    val icon: androidx.compose.ui.graphics.vector.ImageVector,
)

private val bottomDestinations =
    listOf(
        BottomDestination(KastaRoute.Home, "Beranda", Icons.Rounded.Home),
        BottomDestination(KastaRoute.Transactions, "Transaksi", Icons.AutoMirrored.Rounded.ReceiptLong),
        BottomDestination(KastaRoute.Receipt, "Foto Nota", Icons.Rounded.CameraAlt),
        BottomDestination(KastaRoute.Reports, "Laporan", Icons.Rounded.Assessment),
        BottomDestination(KastaRoute.More, "Lainnya", Icons.Rounded.Menu),
    )

@Composable
fun KastaNavigation(
    settingsViewModel: SettingsViewModel,
    initialActionPath: String? = null,
    onActionConsumed: () -> Unit = {},
    navController: NavHostController = rememberNavController(),
) {
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentDestination = backStackEntry?.destination
    val showBottomBar = bottomDestinations.any { item -> currentDestination?.hierarchy?.any { it.route == item.route } == true }
    LaunchedEffect(initialActionPath, currentDestination?.route) {
        if (initialActionPath != null && currentDestination?.route !in setOf(KastaRoute.Splash, KastaRoute.Login)) {
            navController.navigate(routeForAction(initialActionPath)) { launchSingleTop = true }
            onActionConsumed()
        }
    }
    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomDestinations.forEach { item ->
                        val selected = currentDestination?.hierarchy?.any { it.route == item.route } == true
                        NavigationBarItem(
                            selected = selected,
                            onClick = {
                                navController.navigate(item.route) {
                                    popUpTo(KastaRoute.Home) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Icon(item.icon, contentDescription = item.label) },
                            label = { Text(item.label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding)) {
            NavHost(navController = navController, startDestination = KastaRoute.Splash) {
                composable(KastaRoute.Splash) {
                    val auth: AuthViewModel = hiltViewModel()
                    SplashScreen {
                        navController.navigate(
                            when {
                                auth.hasSession() -> KastaRoute.Home
                                auth.hasPendingBusinessSelection() -> KastaRoute.BusinessSelection
                                else -> KastaRoute.Login
                            },
                        ) {
                            popUpTo(KastaRoute.Splash) { inclusive = true }
                        }
                    }
                }
                composable(KastaRoute.Login) {
                    val auth: AuthViewModel = hiltViewModel()
                    val state by auth.state.collectAsState()
                    LaunchedEffect(state.authenticated) {
                        if (state.authenticated) {
                            navController.navigate(KastaRoute.BusinessSelection) { popUpTo(KastaRoute.Login) { inclusive = true } }
                        }
                    }
                    LoginScreen(
                        state = state,
                        onChange = auth::update,
                        onLogin = auth::login,
                        onRegister = { navController.navigate(KastaRoute.Registration) },
                    )
                }
                composable(KastaRoute.BusinessSelection) {
                    val auth: AuthViewModel = hiltViewModel()
                    val state by auth.state.collectAsState()
                    LaunchedEffect(Unit) { auth.loadBusinesses() }
                    LaunchedEffect(state.businessSelected) {
                        if (state.businessSelected) {
                            navController.navigate(KastaRoute.Home) {
                                popUpTo(KastaRoute.BusinessSelection) { inclusive = true }
                            }
                        }
                    }
                    BusinessSelectionScreen(state = state, onSelect = auth::selectBusiness)
                }
                composable(KastaRoute.Registration) {
                    RegistrationScreen(
                        onContinue = { navController.navigate(KastaRoute.Onboarding) },
                        onLogin = { navController.popBackStack() },
                    )
                }
                composable(KastaRoute.Onboarding) {
                    val viewModel: OnboardingViewModel = hiltViewModel()
                    OnboardingScreen(
                        state = viewModel.state.value,
                        onChange = viewModel::update,
                        onCreateAccount = viewModel::createAccount,
                        onVerify = viewModel::verify,
                        onNext = viewModel::next,
                        onBack = viewModel::back,
                        onFinish = viewModel::finish,
                        onOpenTransactions = {
                            viewModel.openTransactions()
                            navController.navigate(KastaRoute.Home) {
                                popUpTo(KastaRoute.Login) { inclusive = true }
                            }
                        },
                    )
                }
                navigation(startDestination = KastaRoute.Home, route = KastaRoute.Main) {
                    composable(KastaRoute.Home) {
                        val viewModel: HomeViewModel = hiltViewModel()
                        val state by viewModel.state.collectAsState()
                        HomeScreen(
                            state = state,
                            onIncome = { navController.navigate(KastaRoute.Income) },
                            onExpense = { navController.navigate(KastaRoute.Expense) },
                            onReceipt = { navController.navigate(KastaRoute.Receipt) },
                            onTransactions = { navController.navigate(KastaRoute.Transactions) },
                        )
                    }
                    composable(KastaRoute.Transactions) { entry ->
                        val viewModel = sharedTransactionViewModel(navController, entry)
                        val state by viewModel.state.collectAsState()
                        LaunchedEffect(Unit) { viewModel.close() }
                        TransactionContent(navController, viewModel, state)
                    }
                    composable(KastaRoute.Income) { entry ->
                        val viewModel = sharedTransactionViewModel(navController, entry)
                        val state by viewModel.state.collectAsState()
                        LaunchedEffect(Unit) { viewModel.start("INCOME") }
                        TransactionContent(navController, viewModel, state)
                    }
                    composable(KastaRoute.Expense) { entry ->
                        val viewModel = sharedTransactionViewModel(navController, entry)
                        val state by viewModel.state.collectAsState()
                        LaunchedEffect(Unit) { viewModel.start("EXPENSE") }
                        TransactionContent(navController, viewModel, state)
                    }
                    composable(KastaRoute.Receipt) { entry ->
                        val parent = remember(entry) { navController.getBackStackEntry(KastaRoute.Main) }
                        val viewModel: ReceiptScanViewModel = hiltViewModel(parent)
                        val state by viewModel.state.collectAsState()
                        LaunchedEffect(Unit) { viewModel.open() }
                        ReceiptScanScreen(
                            state = state,
                            onClose = {
                                viewModel.close()
                                navController.popBackStack()
                            },
                            onDetected = viewModel::documentDetected,
                            onCaptured = viewModel::photoCaptured,
                            onRetry = viewModel::retryUpload,
                            onFieldChange = viewModel::updateField,
                            onChoicesChange = viewModel::updateChoices,
                            onConfirm = viewModel::confirm,
                            onDone = {
                                viewModel.close()
                                navController.navigate(KastaRoute.Transactions)
                            },
                        )
                    }
                    composable(KastaRoute.OcrConfirmation) {
                        OcrConfirmationScreen(
                            onConfirm = { navController.navigate(KastaRoute.Expense) },
                            onBack = { navController.popBackStack() },
                        )
                    }
                    composable(KastaRoute.Reports) { entry ->
                        val parent = remember(entry) { navController.getBackStackEntry(KastaRoute.Main) }
                        val viewModel: ReportViewModel = hiltViewModel(parent)
                        val state by viewModel.state.collectAsState()
                        ReportScreen(
                            state,
                            { navController.popBackStack() },
                            viewModel::updateFilters,
                            viewModel::refresh,
                            viewModel::export,
                        )
                    }
                    composable(KastaRoute.More) { MoreScreen(navController::navigate) }
                    composable(KastaRoute.Products) { entry -> InventoryContent(navController, entry) }
                    composable(KastaRoute.Stock) { entry -> InventoryContent(navController, entry) }
                    composable(KastaRoute.Payables) { entry -> ObligationContent(navController, entry, "PAYABLE") }
                    composable(KastaRoute.Receivables) { entry -> ObligationContent(navController, entry, "RECEIVABLE") }
                    composable(KastaRoute.Mentor) { entry ->
                        val parent = remember(entry) { navController.getBackStackEntry(KastaRoute.Main) }
                        val viewModel: MentorAccessViewModel = hiltViewModel(parent)
                        val state by viewModel.state.collectAsState()
                        MentorAccessScreen(
                            state,
                            { navController.popBackStack() },
                            viewModel::refresh,
                            viewModel::decide,
                            viewModel::revoke,
                        )
                    }
                    composable(KastaRoute.Profile) { ProfileScreen { navController.popBackStack() } }
                    composable(KastaRoute.Settings) {
                        val settings by settingsViewModel.state.collectAsState()
                        val auth: AuthViewModel = hiltViewModel()
                        SettingsScreen(
                            state = settings,
                            onDarkMode = settingsViewModel::setDarkMode,
                            onNotifications = settingsViewModel::setNotifications,
                            onLogout = {
                                auth.logout()
                                navController.navigate(KastaRoute.Login) { popUpTo(KastaRoute.Main) { inclusive = true } }
                            },
                        )
                    }
                    composable(KastaRoute.Sync) { entry ->
                        val viewModel = sharedTransactionViewModel(navController, entry)
                        val state by viewModel.state.collectAsState()
                        SyncStatusScreen(
                            state,
                            { navController.popBackStack() },
                            viewModel::syncNow,
                            viewModel::resolveWithServer,
                            viewModel::resolveWithLocal,
                        )
                    }
                    composable(KastaRoute.Conflicts) { entry ->
                        val viewModel = sharedTransactionViewModel(navController, entry)
                        val state by viewModel.state.collectAsState()
                        ConflictResolutionScreen(
                            state = state,
                            onUseServer = { id -> state.conflicts.find { it.localId == id }?.let(viewModel::resolveWithServer) },
                            onUseLocal = { id -> state.conflicts.find { it.localId == id }?.let(viewModel::resolveWithLocal) },
                            onBack = { navController.popBackStack() },
                        )
                    }
                    composable(KastaRoute.Notifications) {
                        val viewModel: NotificationViewModel = hiltViewModel()
                        val state by viewModel.state.collectAsState()
                        NotificationScreen(
                            state = state,
                            onBack = { navController.popBackStack() },
                            onRefresh = viewModel::refresh,
                            onOpen = { item ->
                                viewModel.markRead(item)
                                navController.navigate(routeForAction(item.actionPath))
                            },
                            onMarkAllRead = viewModel::markAllRead,
                            onCategory = viewModel::setCategory,
                            onReminderTime = viewModel::setReminderTime,
                            onQuietHours = viewModel::setQuietHours,
                        )
                    }
                }
            }
        }
    }
}

private fun routeForAction(path: String?): String =
    when (path) {
        "/transaksi" -> KastaRoute.Transactions
        "/utang" -> KastaRoute.Payables
        "/piutang" -> KastaRoute.Receivables
        "/stok" -> KastaRoute.Stock
        "/foto-nota" -> KastaRoute.Receipt
        "/sinkronisasi" -> KastaRoute.Sync
        "/akses-pembina", "/pembina" -> KastaRoute.Mentor
        "/laporan" -> KastaRoute.Reports
        else -> KastaRoute.Home
    }

@Composable
private fun sharedTransactionViewModel(
    navController: NavHostController,
    entry: androidx.navigation.NavBackStackEntry,
): TransactionViewModel {
    val parent = remember(entry) { navController.getBackStackEntry(KastaRoute.Main) }
    return hiltViewModel(parent)
}

@Composable
private fun TransactionContent(
    navController: NavHostController,
    viewModel: TransactionViewModel,
    state: id.kasta.app.transactions.TransactionUiState,
) {
    TransactionScreen(
        state = state,
        onStart = viewModel::start,
        onOpenReceipt = { navController.navigate(KastaRoute.Receipt) },
        onOpenInventory = { navController.navigate(KastaRoute.Products) },
        onOpenObligations = { navController.navigate(KastaRoute.Receivables) },
        onChange = viewModel::update,
        onNext = viewModel::next,
        onBack = viewModel::back,
        onClose = {
            viewModel.close()
            navController.popBackStack()
        },
        onSave = viewModel::save,
        onPostDraft = viewModel::postDraft,
        onEdit = viewModel::edit,
        onCancel = viewModel::cancel,
        onSearch = viewModel::search,
        onFilter = viewModel::filter,
        onSync = viewModel::syncNow,
        onOpenReports = { navController.navigate(KastaRoute.Reports) },
        onOpenMentorAccess = { navController.navigate(KastaRoute.Mentor) },
        onOpenSyncStatus = { navController.navigate(KastaRoute.Sync) },
    )
}

@Composable
private fun InventoryContent(
    navController: NavHostController,
    entry: androidx.navigation.NavBackStackEntry,
) {
    val parent = remember(entry) { navController.getBackStackEntry(KastaRoute.Main) }
    val viewModel: InventoryViewModel = hiltViewModel(parent)
    val state by viewModel.state.collectAsState()
    if (state.scannerOpen) {
        BarcodeScannerScreen(viewModel::barcodeFound, viewModel::closeScanner)
    } else {
        InventoryScreen(
            state,
            { navController.popBackStack() },
            viewModel::refresh,
            viewModel::filters,
            viewModel::add,
            viewModel::edit,
            viewModel::updateProductForm,
            viewModel::saveProduct,
            viewModel::closeProduct,
            viewModel::openMovement,
            viewModel::updateMovement,
            viewModel::saveMovement,
            viewModel::closeMovement,
            viewModel::openScanner,
        )
    }
}

@Composable
private fun ObligationContent(
    navController: NavHostController,
    entry: androidx.navigation.NavBackStackEntry,
    kind: String,
) {
    val parent = remember(entry) { navController.getBackStackEntry(KastaRoute.Main) }
    val viewModel: ObligationViewModel = hiltViewModel(parent)
    val state by viewModel.state.collectAsState()
    LaunchedEffect(kind) { if (state.kind != kind) viewModel.switchKind(kind) }
    ObligationScreen(
        state,
        { navController.popBackStack() },
        viewModel::switchKind,
        viewModel::refresh,
        viewModel::filters,
        viewModel::openCreate,
        viewModel::updateForm,
        viewModel::save,
        viewModel::closeCreate,
        viewModel::openPayment,
        viewModel::updatePayment,
        viewModel::pay,
        viewModel::closePayment,
        viewModel::history,
        viewModel::closeHistory,
        viewModel::cancel,
    )
}
