import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:real_estate_app/core/api_service.dart';

class CompanyPortfolioScreen extends StatefulWidget {
  final String token;
  final int companyId;

  const CompanyPortfolioScreen({
    Key? key,
    required this.token,
    required this.companyId,
  }) : super(key: key);

  @override
  State<CompanyPortfolioScreen> createState() => _CompanyPortfolioScreenState();
}

class _CompanyPortfolioScreenState extends State<CompanyPortfolioScreen>
    with TickerProviderStateMixin {
  late ApiService _apiService;
  late Future<Map<String, dynamic>> _portfolioFuture;
  late TabController _tabController;

  @override
  void initState() {
    super.initState();
    _apiService = ApiService();
    _portfolioFuture = _apiService.getClientCompanyPortfolio(
      token: widget.token,
      companyId: widget.companyId,
    );
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  String _formatCurrency(dynamic value) {
    if (value == null) return '₦0';
    final num = double.tryParse(value.toString()) ?? 0;
    return '₦${NumberFormat('#,##0').format(num)}';
  }

  Widget _buildCompanyHeader(Map<String, dynamic> company) {
    final logoUrl = company['logo_url'];
    final companyName = company['company_name'] ?? 'Unknown Company';
    final address = company['office_address'] ?? company['location'] ?? 'Address not available';
    final phone = company['phone'];
    final email = company['email'];

    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        children: [
          // Company Logo/Initials
          Container(
            width: 80,
            height: 80,
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(8),
              gradient: logoUrl != null && logoUrl.isNotEmpty
                  ? null
                  : const LinearGradient(
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                      colors: [Color(0xFF10B981), Color(0xFF059669)],
                    ),
              image: logoUrl != null && logoUrl.isNotEmpty
                  ? DecorationImage(
                      image: NetworkImage(logoUrl),
                      fit: BoxFit.cover,
                    )
                  : null,
            ),
            child: logoUrl == null || logoUrl.isEmpty
                ? Center(
                    child: Text(
                      companyName.isNotEmpty ? companyName[0].toUpperCase() : '?',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 32,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  )
                : null,
          ),
          const SizedBox(width: 20),
          // Company Info
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  companyName,
                  style: const TextStyle(
                    fontSize: 24,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF081226),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  address,
                  style: const TextStyle(
                    fontSize: 14,
                    color: Color(0xFF6C757D),
                  ),
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    if (phone != null && phone.isNotEmpty) ...[
                      const Icon(Icons.phone, size: 16, color: Color(0xFF10B981)),
                      const SizedBox(width: 4),
                      Text(
                        phone,
                        style: const TextStyle(
                          fontSize: 14,
                          color: Color(0xFF10B981),
                        ),
                      ),
                      const SizedBox(width: 16),
                    ],
                    if (email != null && email.isNotEmpty) ...[
                      const Icon(Icons.email, size: 16, color: Color(0xFF10B981)),
                      const SizedBox(width: 4),
                      Text(
                        email,
                        style: const TextStyle(
                          fontSize: 14,
                          color: Color(0xFF10B981),
                        ),
                      ),
                    ],
                  ],
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatsCards(Map<String, dynamic> stats) {
    final totalInvested = stats['total_invested'] ?? 0;
    final totalAppreciation = stats['total_appreciation'] ?? 0;
    final totalCurrentValue = stats['total_current_value'] ?? 0;
    final marketer = stats['marketer'];

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        children: [
          Expanded(
            child: _buildStatCard(
              'Total Invested',
              _formatCurrency(totalInvested),
              'Across all purchases',
              Colors.white,
              const Color(0xFF081226),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              'Total Appreciation',
              _formatCurrency(totalAppreciation),
              'Current Value minus Invested',
              const Color(0xFFD1FAE5),
              const Color(0xFF065F46),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              'Total Current Value',
              _formatCurrency(totalCurrentValue),
              'Current market value',
              Colors.white,
              const Color(0xFF081226),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: _buildStatCard(
              'Your Marketer',
              marketer?['full_name'] ?? 'No marketer',
              marketer?['email'] ?? '',
              const Color(0xFFDBEAFE),
              const Color(0xFF1E40AF),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildStatCard(String title, String value, String subtitle, Color bgColor, Color textColor) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE9ECEF)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF6C757D),
              fontWeight: FontWeight.w500,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            value,
            style: TextStyle(
              fontSize: 18,
              fontWeight: FontWeight.bold,
              color: textColor,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtitle,
            style: const TextStyle(
              fontSize: 10,
              color: Color(0xFF6C757D),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildPropertiesTab(List<dynamic> transactions) {
    if (transactions.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.house_outlined, size: 64, color: Color(0xFF6C757D)),
            SizedBox(height: 16),
            Text(
              'No properties found',
              style: TextStyle(
                fontSize: 18,
                color: Color(0xFF6C757D),
              ),
            ),
          ],
        ),
      );
    }

    return ListView.builder(
      padding: const EdgeInsets.all(16),
      itemCount: transactions.length,
      itemBuilder: (context, index) {
        final transaction = transactions[index] as Map<String, dynamic>;
        return _buildPropertyCard(transaction);
      },
    );
  }

  Widget _buildPropertyCard(Map<String, dynamic> transaction) {
    final allocation = transaction['allocation'] as Map<String, dynamic>? ?? {};
    final estate = allocation['estate'] as Map<String, dynamic>? ?? {};
    final plotSize = allocation['plot_size'] as Map<String, dynamic>? ?? {};
    final plotNumber = allocation['plot_number'] as Map<String, dynamic>?;

    final estateName = estate['name'] ?? 'Unknown Estate';
    final plotSizeName = plotSize['size'] ?? 'Unknown Size';
    final plotNumberValue = plotNumber?['number']?.toString() ?? 'Reserved';
    final totalAmount = transaction['total_amount'] ?? 0;
    final currentValue = transaction['current_value'];
    final status = transaction['status'] ?? 'Unknown';
    final transactionDate = transaction['transaction_date'];

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE9ECEF)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Column(
        children: [
          Row(
            children: [
              // Property Icon
              Container(
                width: 50,
                height: 50,
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(12),
                  gradient: const LinearGradient(
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                    colors: [Color(0xFF10B981), Color(0xFF059669)],
                  ),
                ),
                child: const Icon(
                  Icons.business,
                  color: Colors.white,
                  size: 24,
                ),
              ),
              const SizedBox(width: 16),
              // Property Info
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      estateName,
                      style: const TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF081226),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF8F9FA),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            plotSizeName,
                            style: const TextStyle(
                              fontSize: 12,
                              color: Color(0xFF081226),
                            ),
                          ),
                        ),
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                          decoration: BoxDecoration(
                            color: plotNumber != null ? const Color(0xFF10B981) : const Color(0xFFFFC107),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            plotNumber != null ? 'Plot $plotNumberValue' : 'Reserved',
                            style: const TextStyle(
                              fontSize: 12,
                              color: Colors.white,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Price Info
          Row(
            children: [
              Expanded(
                child: Column(
                  children: [
                    const Text(
                      'Purchase Price',
                      style: TextStyle(
                        fontSize: 12,
                        color: Color(0xFF6C757D),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      _formatCurrency(totalAmount),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF081226),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  children: [
                    const Text(
                      'Current Value',
                      style: TextStyle(
                        fontSize: 12,
                        color: Color(0xFF6C757D),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      currentValue != null ? _formatCurrency(currentValue) : '-',
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF10B981),
                      ),
                    ),
                  ],
                ),
              ),
              Expanded(
                child: Column(
                  children: [
                    const Text(
                      'Date',
                      style: TextStyle(
                        fontSize: 12,
                        color: Color(0xFF6C757D),
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      transactionDate != null
                          ? DateFormat('MMM d, y').format(DateTime.parse(transactionDate))
                          : '-',
                      style: const TextStyle(
                        fontSize: 12,
                        color: Color(0xFF081226),
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: 16),
          // Status and Actions
          Row(
            children: [
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                decoration: BoxDecoration(
                  color: _getStatusColor(status),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  status,
                  style: const TextStyle(
                    fontSize: 12,
                    color: Colors.white,
                    fontWeight: FontWeight.w500,
                  ),
                ),
              ),
              const Spacer(),
              IconButton(
                onPressed: () => _showTransactionDetails(transaction['id']),
                icon: const Icon(Icons.receipt, color: Color(0xFF10B981)),
                tooltip: 'View Receipt',
              ),
              if (allocation.isNotEmpty)
                IconButton(
                  onPressed: () {
                    // Navigate to plot details
                  },
                  icon: const Icon(Icons.visibility, color: Color(0xFF10B981)),
                  tooltip: 'View Details',
                ),
            ],
          ),
        ],
      ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'paid complete':
      case 'fully paid':
        return const Color(0xFF10B981);
      case 'overdue':
        return const Color(0xFFDC3545);
      case 'part payment':
        return const Color(0xFFFFC107);
      default:
        return const Color(0xFF6C757D);
    }
  }

  Widget _buildAppreciationTab(List<dynamic> appreciationData) {
    if (appreciationData.isEmpty) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.trending_up, size: 64, color: Color(0xFF6C757D)),
            SizedBox(height: 16),
            Text(
              'No appreciation data available',
              style: TextStyle(
                fontSize: 18,
                color: Color(0xFF6C757D),
              ),
            ),
          ],
        ),
      );
    }

    return GridView.builder(
      padding: const EdgeInsets.all(16),
      gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
        crossAxisCount: 2,
        crossAxisSpacing: 16,
        mainAxisSpacing: 16,
        childAspectRatio: 0.8,
      ),
      itemCount: appreciationData.length,
      itemBuilder: (context, index) {
        final data = appreciationData[index] as Map<String, dynamic>;
        return _buildAppreciationCard(data);
      },
    );
  }

  Widget _buildAppreciationCard(Map<String, dynamic> data) {
    final estate = data['estate'] as Map<String, dynamic>? ?? {};
    final plotSize = data['plot_size'] as Map<String, dynamic>? ?? {};
    final purchasePrice = data['purchase_price'] ?? 0;
    final currentValue = data['current_value'] ?? 0;
    final appreciation = data['appreciation'] ?? 0;
    final growthRate = data['growth_rate'] ?? 0;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.05),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.business, color: Color(0xFF10B981), size: 20),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  estate['name'] ?? 'Unknown Estate',
                  style: const TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF081226),
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
            decoration: BoxDecoration(
              color: const Color(0xFFF8F9FA),
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              plotSize['size'] ?? 'Unknown Size',
              style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF081226),
              ),
            ),
          ),
          const SizedBox(height: 16),
          _buildAppreciationItem('Purchase Price', _formatCurrency(purchasePrice)),
          _buildAppreciationItem('Current Value', _formatCurrency(currentValue)),
          _buildAppreciationItem(
            'Value Increase',
            '${appreciation >= 0 ? '+' : '-'}${_formatCurrency(appreciation.abs())}',
            color: appreciation >= 0 ? const Color(0xFF10B981) : const Color(0xFFDC3545),
          ),
          _buildAppreciationItem(
            'Growth Rate',
            '${growthRate >= 0 ? '+' : ''}${growthRate.toStringAsFixed(2)}%',
            color: growthRate >= 0 ? const Color(0xFF10B981) : const Color(0xFFDC3545),
          ),
          const SizedBox(height: 16),
          // Progress bar
          Container(
            height: 6,
            decoration: BoxDecoration(
              color: const Color(0xFFE9ECEF),
              borderRadius: BorderRadius.circular(3),
            ),
            child: FractionallySizedBox(
              alignment: Alignment.centerLeft,
              widthFactor: (growthRate.abs() / 100).clamp(0.0, 1.0),
              child: Container(
                decoration: BoxDecoration(
                  color: growthRate >= 0 ? const Color(0xFF10B981) : const Color(0xFFDC3545),
                  borderRadius: BorderRadius.circular(3),
                ),
              ),
            ),
          ),
          const SizedBox(height: 8),
          const Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                'Purchase',
                style: TextStyle(fontSize: 10, color: Color(0xFF6C757D)),
              ),
              Text(
                'Current',
                style: TextStyle(fontSize: 10, color: Color(0xFF6C757D)),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAppreciationItem(String label, String value, {Color? color}) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: const TextStyle(
              fontSize: 12,
              color: Color(0xFF6C757D),
            ),
          ),
          Text(
            value,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.bold,
              color: color ?? const Color(0xFF081226),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRightColumn(Map<String, dynamic> data) {
    final company = data['company'] as Map<String, dynamic>? ?? {};
    final estatesCount = data['estates_count'] ?? 0;
    final paymentsByYear = data['payments_by_year'] as Map<String, dynamic>? ?? {};

    return Container(
      width: 300,
      padding: const EdgeInsets.all(16),
      child: Column(
        children: [
          // Company Summary
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE9ECEF)),
            ),
            child: Column(
              children: [
                const Text(
                  'Company Summary',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF081226),
                  ),
                ),
                const SizedBox(height: 8),
                Text(
                  company['company_name'] ?? 'Unknown Company',
                  style: const TextStyle(
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF10B981),
                  ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 4),
                Text(
                  'Owned Estates: $estatesCount',
                  style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFF6C757D),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          // Recent Payments
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: const Color(0xFFE9ECEF)),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Recent Payments',
                  style: TextStyle(
                    fontSize: 14,
                    fontWeight: FontWeight.bold,
                    color: Color(0xFF081226),
                  ),
                ),
                const SizedBox(height: 16),
                if (paymentsByYear.isEmpty)
                  const Center(
                    child: Padding(
                      padding: EdgeInsets.all(16),
                      child: Column(
                        children: [
                          Icon(Icons.inbox, size: 32, color: Color(0xFF6C757D)),
                          SizedBox(height: 8),
                          Text(
                            'No payments yet',
                            style: TextStyle(
                              fontSize: 12,
                              color: Color(0xFF6C757D),
                            ),
                          ),
                        ],
                      ),
                    ),
                  )
                else
                  ...paymentsByYear.entries.map((entry) {
                    final year = entry.key;
                    final payments = entry.value as List<dynamic>;
                    return _buildYearAccordion(year, payments);
                  }),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildYearAccordion(String year, List<dynamic> payments) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        border: Border.all(color: const Color(0xFFE9ECEF)),
        borderRadius: BorderRadius.circular(8),
      ),
      child: ExpansionTile(
        title: Row(
          children: [
            const Icon(Icons.calendar_today, size: 16, color: Color(0xFF10B981)),
            const SizedBox(width: 8),
            Text(
              year,
              style: const TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.bold,
                color: Color(0xFF081226),
              ),
            ),
            const Spacer(),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                color: const Color(0xFF10B981),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text(
                '${payments.length}',
                style: const TextStyle(
                  fontSize: 12,
                  color: Colors.white,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        children: payments.map((payment) {
          final paymentMap = payment as Map<String, dynamic>;
          return Container(
            padding: const EdgeInsets.all(12),
            decoration: const BoxDecoration(
              border: Border(top: BorderSide(color: Color(0xFFE9ECEF))),
            ),
            child: Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        paymentMap['reference_code'] ?? '',
                        style: const TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.bold,
                          color: Color(0xFF081226),
                        ),
                      ),
                      Text(
                        paymentMap['date'] != null
                            ? DateFormat('d MMM y').format(DateTime.parse(paymentMap['date']))
                            : '',
                        style: const TextStyle(
                          fontSize: 10,
                          color: Color(0xFF6C757D),
                        ),
                      ),
                      Container(
                        margin: const EdgeInsets.only(top: 4),
                        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                        decoration: BoxDecoration(
                          color: paymentMap['payment_type'] == 'Full Payment'
                              ? const Color(0xFF10B981)
                              : const Color(0xFF17A2B8),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          paymentMap['payment_type'] ?? '',
                          style: const TextStyle(
                            fontSize: 10,
                            color: Colors.white,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    Text(
                      _formatCurrency(paymentMap['amount']),
                      style: const TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF10B981),
                      ),
                    ),
                    Container(
                      margin: const EdgeInsets.only(top: 4),
                      padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                      decoration: BoxDecoration(
                        color: _getPaymentStatusColor(paymentMap['status'] ?? ''),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        paymentMap['status'] ?? '',
                        style: const TextStyle(
                          fontSize: 10,
                          color: Colors.white,
                        ),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          );
        }).toList(),
      ),
    );
  }

  Color _getPaymentStatusColor(String status) {
    switch (status.toLowerCase()) {
      case 'paid':
      case 'paid complete':
      case 'fully paid':
        return const Color(0xFF10B981);
      case 'overdue':
        return const Color(0xFFDC3545);
      default:
        return const Color(0xFFFFC107);
    }
  }

  void _showTransactionDetails(int transactionId) async {
    try {
      final details = await _apiService.getClientCompanyTransactionDetail(
        token: widget.token,
        transactionId: transactionId,
      );

      showDialog(
        context: context,
        builder: (context) => AlertDialog(
          title: const Text('Transaction Details'),
          content: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                _buildDetailRow('Estate', details['allocation']?['estate']?['name'] ?? ''),
                _buildDetailRow('Plot Size', details['allocation']?['plot_size']?['size'] ?? ''),
                _buildDetailRow('Date', details['transaction_date'] ?? ''),
                _buildDetailRow('Amount', _formatCurrency(details['total_amount'])),
                _buildDetailRow('Status', details['status'] ?? ''),
                if (details['allocation']?['payment_type'] == 'part') ...[
                  _buildDetailRow('Duration', '${details['payment_duration'] ?? 0} months'),
                  _buildDetailRow('Plan', details['installment_plan'] ?? ''),
                ],
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.of(context).pop(),
              child: const Text('Close'),
            ),
          ],
        ),
      );
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('Error loading transaction details: $e')),
      );
    }
  }

  Widget _buildDetailRow(String label, String value) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 80,
            child: Text(
              '$label:',
              style: const TextStyle(fontWeight: FontWeight.bold),
            ),
          ),
          Expanded(child: Text(value)),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('My Portfolio'),
        backgroundColor: Colors.white,
        elevation: 0,
        foregroundColor: const Color(0xFF081226),
      ),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _portfolioFuture,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(
              child: CircularProgressIndicator(
                valueColor: AlwaysStoppedAnimation<Color>(Color(0xFF10B981)),
              ),
            );
          }

          if (snapshot.hasError) {
            return Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.error_outline, size: 64, color: Color(0xFFDC3545)),
                  const SizedBox(height: 16),
                  Text(
                    'Error loading portfolio: ${snapshot.error}',
                    style: const TextStyle(color: Color(0xFFDC3545)),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () {
                      setState(() {
                        _portfolioFuture = _apiService.getClientCompanyPortfolio(
                          token: widget.token,
                          companyId: widget.companyId,
                        );
                      });
                    },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF10B981),
                    ),
                    child: const Text('Retry'),
                  ),
                ],
              ),
            );
          }

          final data = snapshot.data ?? {};
          final company = data['company'] as Map<String, dynamic>? ?? {};
          final stats = data['stats'] as Map<String, dynamic>? ?? {};
          final transactions = data['properties'] as List<dynamic>? ?? [];
          final appreciationData = data['appreciation_data'] as List<dynamic>? ?? [];

          return Row(
            children: [
              // Main content
              Expanded(
                child: SingleChildScrollView(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      _buildCompanyHeader(company),
                      _buildStatsCards(stats),
                      Container(
                        margin: const EdgeInsets.all(16),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(color: const Color(0xFFE9ECEF)),
                        ),
                        child: Column(
                          children: [
                            TabBar(
                              controller: _tabController,
                              tabs: const [
                                Tab(text: 'Properties'),
                                Tab(text: 'Value Appreciation'),
                              ],
                              labelColor: const Color(0xFF10B981),
                              unselectedLabelColor: const Color(0xFF6C757D),
                              indicatorColor: const Color(0xFF10B981),
                            ),
                            SizedBox(
                              height: 600,
                              child: TabBarView(
                                controller: _tabController,
                                children: [
                                  _buildPropertiesTab(transactions),
                                  _buildAppreciationTab(appreciationData),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              // Right column
              _buildRightColumn(data),
            ],
          );
        },
      ),
    );
  }
}