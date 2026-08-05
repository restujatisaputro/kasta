export interface HealthResponse {
  status: 'ok';
  service: 'kasta-api';
  version: string;
  timestamp: string;
}

export interface ProblemDetails {
  type: string;
  title: string;
  status: number;
  detail?: string;
  instance?: string;
  code?: string;
  correlationId?: string;
  fieldErrors?: Record<string, string[]>;
}

export type BusinessType =
  'TRADE' | 'SERVICE' | 'PRODUCTION' | 'CULINARY' | 'AGRICULTURE' | 'CREATIVE' | 'OTHER';
export type BusinessScale = 'MICRO' | 'SMALL' | 'MEDIUM';
export type PaymentMethodCode = 'CASH' | 'BANK_TRANSFER' | 'QRIS' | 'E_WALLET' | 'CARD';

export interface BusinessCategory {
  id: string;
  code: string;
  name: string;
  business_type: BusinessType;
  display_order: number;
}

export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface BusinessAccess {
  business_id: string;
  code: string;
  name: string;
  role: string;
}

export interface AccessToken {
  access_token: string;
  token_type: 'bearer';
  expires_in: number;
}

export interface BusinessProfile {
  business_id: string;
  name: string;
  logo_path: string | null;
  business_type: BusinessType;
  category_id: string;
  category_name: string;
  scale: BusinessScale;
  established_year: number | null;
  address: string | null;
  village: string | null;
  district: string | null;
  city: string;
  province: string;
  phone: string | null;
  email: string | null;
  employee_count: number;
  currency: 'IDR' | 'USD' | 'SGD' | 'MYR';
  timezone: 'Asia/Jakarta' | 'Asia/Makassar' | 'Asia/Jayapura';
  recording_method: 'CASH' | 'ACCRUAL';
  status: 'ACTIVE' | 'INACTIVE';
  payment_methods: PaymentMethodCode[];
  opening_balance: string;
  has_products_and_stock: boolean;
  tutorial_completed_at: string | null;
  onboarding_completed_at: string;
}

export interface CompleteOnboardingResponse {
  business_id: string;
  profile: BusinessProfile;
  tokens: TokenPair;
  next_path: string;
}

export type EntryKind = 'INCOME' | 'EXPENSE' | 'CAPITAL' | 'OWNER_DRAW';
export type TransactionStatus = 'POSTED' | 'REVERSED';
export type TransactionPaymentMethod = 'CASH' | 'BANK_TRANSFER' | 'QRIS' | 'E_WALLET' | 'CARD';
export type RecurrenceFrequency = 'WEEKLY' | 'MONTHLY';

export interface OptionItem {
  value: string;
  label: string;
}

export interface TransactionOptions {
  income_sources: OptionItem[];
  expense_categories: OptionItem[];
  payment_methods: OptionItem[];
}

export interface SimpleTransactionInput {
  entry_kind: EntryKind;
  transaction_date: string;
  amount: string;
  category_account?: string | null;
  counterparty_name?: string | null;
  payment_method: TransactionPaymentMethod;
  note: string;
  recurrence_frequency?: RecurrenceFrequency | null;
  recurrence_interval?: number | null;
  idempotency_key?: string | null;
  items?: TransactionProductItemInput[];
}

export interface TransactionProductItemInput {
  product_id: string;
  quantity: string;
  unit_price: string;
}

export interface FinancialTransaction {
  id: string;
  business_id: string;
  transaction_number: string;
  transaction_type: string;
  transaction_date: string;
  amount: string;
  description: string;
  status: TransactionStatus;
  revision_number: number;
  root_transaction_id: string | null;
  supersedes_transaction_id: string | null;
  reverses_transaction_id: string | null;
  reversed_by_transaction_id: string | null;
  posted_at: string;
  entry_kind: EntryKind | null;
  counterparty_name: string | null;
  payment_method_code: TransactionPaymentMethod | null;
  recurring_rule_id: string | null;
  category_account_key: string | null;
}

export interface TransactionListItem extends FinancialTransaction {
  receipt_count: number;
  items: TransactionProductItem[];
}

export interface TransactionProductItem extends TransactionProductItemInput {
  line_total: string;
  stock_direction: 'IN' | 'OUT';
}

export interface TransactionListResponse {
  items: TransactionListItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface RecurringTransaction {
  id: string;
  business_id: string;
  entry_kind: EntryKind;
  amount: string;
  category_account_key: string | null;
  counterparty_name: string | null;
  payment_method_code: TransactionPaymentMethod;
  note: string;
  frequency: RecurrenceFrequency;
  recurrence_interval: number;
  next_run_date: string;
  last_run_at: string | null;
  status: 'ACTIVE' | 'PAUSED' | 'CANCELLED';
}

export interface SimpleTransactionResponse {
  transaction: FinancialTransaction;
  recurring: RecurringTransaction | null;
}

export interface TransactionDraft {
  id: string;
  business_id: string;
  client_reference: string | null;
  entry_kind: EntryKind;
  transaction_date: string;
  amount: string;
  category_account_key: string | null;
  counterparty_name: string | null;
  payment_method_code: TransactionPaymentMethod;
  note: string;
  recurrence_frequency: RecurrenceFrequency | null;
  recurrence_interval: number | null;
  status: 'ACTIVE' | 'POSTED';
  items_data: TransactionProductItemInput[] | null;
  posted_transaction_id: string | null;
  created_at: string;
  updated_at: string;
}

export type ProductUnit =
  'PCS' | 'BOX' | 'PACK' | 'KG' | 'GRAM' | 'LITER' | 'ML' | 'METER' | 'SET' | 'UNIT';

export interface Product {
  id: string;
  business_id: string;
  sku: string;
  barcode: string | null;
  name: string;
  category: string;
  unit: ProductUnit;
  purchase_price: string;
  sale_price: string;
  opening_stock: string;
  current_stock: string;
  minimum_stock: string;
  is_active: boolean;
  is_low_stock: boolean;
  inventory_value: string;
  created_at: string;
  updated_at: string;
}

export interface ProductListResponse {
  items: Product[];
  total: number;
  limit: number;
  offset: number;
}

export interface ProductInput {
  sku: string;
  barcode?: string | null;
  name: string;
  category: string;
  unit: ProductUnit;
  purchase_price: string;
  sale_price: string;
  opening_stock?: string;
  minimum_stock: string;
  is_active: boolean;
}

export type StockMovementInput =
  | {
      movement_type: 'STOCK_IN' | 'STOCK_OUT' | 'DAMAGED' | 'LOST';
      quantity: string;
      target_stock?: null;
      unit_cost?: string | null;
      reason: string;
      reference?: string;
    }
  | {
      movement_type: 'ADJUSTMENT';
      quantity?: null;
      target_stock: string;
      unit_cost?: string | null;
      reason: string;
      reference?: string;
    };

export interface StockMovement {
  id: string;
  business_id: string;
  product_id: string;
  transaction_id: string | null;
  movement_type: string;
  quantity_delta: string;
  stock_before: string;
  stock_after: string;
  unit_cost: string;
  total_cost: string;
  reason: string | null;
  reference: string | null;
  occurred_at: string;
  created_by_user_id: string;
  created_at: string;
}

export interface StockHistoryResponse {
  items: StockMovement[];
  total: number;
  limit: number;
  offset: number;
}

export interface BestSeller {
  product_id: string;
  sku: string;
  name: string;
  unit: string;
  quantity_sold: string;
  sales_value: string;
}

export interface InventorySummary {
  product_count: number;
  active_product_count: number;
  low_stock_count: number;
  inventory_value: string;
  best_sellers: BestSeller[];
}

export interface CsvImportResponse {
  imported_count: number;
  product_ids: string[];
}

export type ObligationKind = 'RECEIVABLE' | 'PAYABLE';
export type ObligationStatus = 'OPEN' | 'PARTIALLY_PAID' | 'PAID' | 'OVERDUE' | 'CANCELLED';

export interface ObligationParty {
  id: string;
  name: string;
  phone: string | null;
  email: string | null;
  is_active: boolean;
}

export interface ObligationPayment {
  id: string;
  transaction_id: string;
  amount: string;
  payment_date: string;
  payment_account_key: 'CASH' | 'BANK';
  note: string | null;
  created_by_user_id: string;
  created_at: string;
}

export interface Obligation {
  id: string;
  business_id: string;
  kind: ObligationKind;
  party: ObligationParty;
  initial_transaction_id: string;
  cancellation_transaction_id: string | null;
  initial_amount: string;
  paid_amount: string;
  remaining_amount: string;
  transaction_date: string;
  due_date: string;
  status: ObligationStatus;
  status_label: string;
  note: string | null;
  reminder_enabled: boolean;
  reminder_days_before: number;
  days_until_due: number;
  created_at: string;
  updated_at: string;
}

export interface ObligationDetail extends Obligation {
  payments: ObligationPayment[];
}

export interface ObligationListResponse {
  items: Obligation[];
  total: number;
  limit: number;
  offset: number;
}

export interface ObligationInput {
  party_id?: string | null;
  party_name?: string;
  party_phone?: string;
  party_email?: string;
  initial_amount: string;
  transaction_date: string;
  due_date: string;
  note?: string;
  reminder_enabled: boolean;
  reminder_days_before: number;
}

export interface ObligationPaymentInput {
  amount: string;
  payment_date: string;
  payment_account: 'CASH' | 'BANK';
  note?: string;
}

export interface AgingBucket {
  code: 'NOT_DUE' | 'DUE_1_30' | 'DUE_31_60' | 'DUE_61_90' | 'DUE_OVER_90';
  label: string;
  count: number;
  amount: string;
}

export interface AgingSection {
  total_open: string;
  buckets: AgingBucket[];
}

export interface ObligationAgingReport {
  as_of: string;
  receivables: AgingSection;
  payables: AgingSection;
}

export interface ObligationReminder {
  kind: ObligationKind;
  obligation_id: string;
  party_name: string;
  due_date: string;
  remaining_amount: string;
  days_until_due: number;
  message: string;
}

export interface ObligationReminderList {
  as_of: string;
  items: ObligationReminder[];
}

export type ReportPeriod = 'DAY' | 'WEEK' | 'MONTH' | 'QUARTER' | 'YEAR' | 'CUSTOM';
export type ReportExportFormat = 'PDF' | 'XLSX' | 'CSV';

export interface ReportFilters {
  period: ReportPeriod;
  reference_date?: string;
  date_from?: string;
  date_to?: string;
  category?: string;
  payment_method?: string;
  branch_id?: string;
}

export interface AccountReportLine {
  account_key: string;
  account_name: string;
  amount: string;
}

export interface CategoryTotal {
  key: string;
  label: string;
  amount: string;
  percentage: string;
}

export interface ReportTimePoint {
  period: string;
  income: string;
  expense: string;
  profit: string;
  sales: string;
}

export interface ProductPerformance {
  product_id: string;
  sku: string;
  name: string;
  unit: string;
  quantity_sold: string;
  sales_value: string;
}

export interface FinancialReport {
  context: {
    business_id: string;
    business_name: string;
    period: ReportPeriod;
    date_from: string;
    date_to: string;
    category: string | null;
    payment_method: string | null;
    branch_id: string;
    branch_name: string;
    generated_at: string;
    source: 'JOURNAL';
  };
  summary: {
    income: string;
    expense: string;
    estimated_profit: string;
    cash_in: string;
    cash_out: string;
    net_cash_flow: string;
    receivables: string;
    payables: string;
    inventory_value: string;
  };
  profit_loss: {
    revenues: AccountReportLine[];
    expenses: AccountReportLine[];
    total_revenue: string;
    total_expense: string;
    profit: string;
    explanation: string;
  };
  balance_sheet: {
    assets: AccountReportLine[];
    liabilities: AccountReportLine[];
    equity: AccountReportLine[];
    total_assets: string;
    total_liabilities: string;
    total_equity: string;
    difference: string;
    explanation: string;
  };
  cash_flow: {
    cash_in: string;
    cash_out: string;
    net_cash_flow: string;
    ending_cash_balance: string;
    explanation: string;
  };
  sales: CategoryTotal[];
  expenditures: CategoryTotal[];
  receivables: ObligationReport;
  payables: ObligationReport;
  inventory: {
    product_count: number;
    low_stock_count: number;
    total_quantity: string;
    operational_value: string;
    journal_value: string;
    explanation: string;
  };
  best_selling_products: ProductPerformance[];
  monthly_comparison: ReportTimePoint[];
  charts: {
    income_vs_expense: ReportTimePoint[];
    profit_trend: ReportTimePoint[];
    expense_categories: CategoryTotal[];
    daily_sales: ReportTimePoint[];
    best_selling_products: ProductPerformance[];
  };
  explanation: string;
}

export interface ObligationReport {
  open_count: number;
  overdue_count: number;
  total_initial: string;
  total_paid: string;
  total_remaining: string;
  journal_value: string;
  explanation: string;
}

export type ReceiptScanStatus = 'UPLOADED' | 'PROCESSING' | 'NEEDS_REVIEW' | 'CONFIRMED' | 'FAILED';

export interface ReceiptOcrField {
  name: string;
  value: string;
  confidence: string;
  source_text: string | null;
  corrected_value: string | null;
}

export interface ReceiptOcrItem {
  line_number: number;
  description: string;
  quantity: string | null;
  unit_price: string | null;
  line_total: string;
  confidence: string;
}

export interface DuplicateReceipt {
  id: string;
  merchant_name: string | null;
  receipt_date: string | null;
  receipt_number: string | null;
  total_amount: string | null;
  hash_distance: number | null;
  match_reasons: Array<'gambar_mirip' | 'tanggal' | 'total' | 'nama_toko' | 'nomor_nota'>;
}

export interface ReceiptReview {
  id: string;
  business_id: string;
  status: ReceiptScanStatus;
  transaction_id: string | null;
  fields: ReceiptOcrField[];
  items: ReceiptOcrItem[];
  duplicate_candidates: DuplicateReceipt[];
  processing_duration_ms: number | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConfirmReceiptRequest {
  corrections: Partial<Record<string, string | null>>;
  entry_kind?: Extract<EntryKind, 'INCOME' | 'EXPENSE'>;
  category_account?: string;
  payment_method?: TransactionPaymentMethod;
  note?: string;
  acknowledge_duplicate?: boolean;
}

export interface ConfirmReceiptResponse {
  receipt: ReceiptReview;
  transaction_id: string;
}

export type MentorHealthLevel = 'GREEN' | 'YELLOW' | 'RED';
export type RecommendationStatus = 'OPEN' | 'IN_PROGRESS' | 'DONE' | 'CANCELLED';
export type MentoringSessionStatus = 'SCHEDULED' | 'COMPLETED' | 'CANCELLED';

export interface MentorRiskIndicator {
  code: string;
  level: MentorHealthLevel;
  label: string;
  message: string;
  icon: string;
}

export interface MentorTrendPoint {
  month: string;
  revenue: string;
  expense: string;
  profit: string;
}

export interface MentorBusinessSummary {
  business_id: string;
  business_name: string;
  city: string | null;
  province: string | null;
  health_level: MentorHealthLevel;
  health_label: string;
  health_icon: string;
  last_recorded_date: string | null;
  days_since_recording: number | null;
  recording_consistency: string;
  month_revenue: string;
  month_expense: string;
  month_profit: string;
  payable_balance: string;
  receivable_balance: string;
  overdue_receivable: string;
  open_recommendations: number;
  risk_indicators: MentorRiskIndicator[];
}

export interface MentorNote {
  id: string;
  business_id: string;
  mentor_id: string;
  content: string;
  visibility: 'SHARED' | 'PRIVATE';
  created_at: string;
}

export interface MentorRecommendation {
  id: string;
  business_id: string;
  mentor_id: string;
  title: string;
  description: string;
  priority: 'LOW' | 'MEDIUM' | 'HIGH';
  status: RecommendationStatus;
  due_date: string | null;
  follow_up_note: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MentoringSession {
  id: string;
  business_id: string;
  mentor_id: string;
  scheduled_at: string;
  duration_minutes: number;
  mode: 'ONSITE' | 'ONLINE' | 'PHONE';
  status: MentoringSessionStatus;
  topic: string;
  location: string | null;
  outcome: string | null;
  follow_up_date: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface MentorBusinessDetail {
  summary: MentorBusinessSummary;
  revenue_trend: MentorTrendPoint[];
  notes: MentorNote[];
  recommendations: MentorRecommendation[];
  sessions: MentoringSession[];
  explanation: string;
}

export interface MentorScheduleItem {
  id: string;
  business_id: string;
  business_name: string;
  scheduled_at: string;
  duration_minutes: number;
  mode: string;
  topic: string;
}

export interface MentorDashboard {
  total_businesses: number;
  active_businesses: number;
  stale_businesses: number;
  expense_over_income: number;
  high_debt: number;
  overdue_receivables: number;
  open_recommendations: number;
  health_green: number;
  health_yellow: number;
  health_red: number;
  upcoming_sessions: MentorScheduleItem[];
  businesses: MentorBusinessSummary[];
  generated_at: string;
}

export interface MentorAggregateReport {
  dashboard: MentorDashboard;
  total_revenue: string;
  total_expense: string;
  total_profit: string;
  total_payables: string;
  total_receivables: string;
  explanation: string;
}

export interface MentorAuditActivity {
  id: string;
  business_id: string;
  business_name: string;
  action: string;
  entity_type: string;
  entity_id: string;
  reason: string | null;
  created_at: string;
}

export type MentorAccessScope =
  | 'SUMMARY'
  | 'REPORTS'
  | 'TRANSACTIONS'
  | 'RECEIPTS'
  | 'INVENTORY'
  | 'OBLIGATIONS'
  | 'EXPORT_REPORTS';
export type MentorAccessStatus = 'REQUESTED' | 'ACTIVE' | 'REJECTED' | 'REVOKED' | 'EXPIRED';

export interface MentorAccessGrant {
  id: string;
  business_id: string;
  mentor_id: string;
  requested_by_user_id: string;
  granted_by_user_id: string | null;
  scope: MentorAccessScope[];
  status: MentorAccessStatus;
  request_message: string | null;
  requested_at: string;
  granted_at: string | null;
  expires_at: string | null;
  revoked_at: string | null;
  rejection_reason: string | null;
  revocation_reason: string | null;
  last_accessed_at: string | null;
  revision_no: number;
}

export interface MentorAccessHistory {
  id: string;
  action: string;
  mentor_id: string | null;
  actor_user_id: string | null;
  scope: string[];
  reason: string | null;
  accessed_at: string;
}
