import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:real_estate_app/core/api_service.dart';

class MarketerMyCompaniesScreen extends StatefulWidget {
  final String token;
  const MarketerMyCompaniesScreen({Key? key, required this.token})
      : super(key: key);

  @override
  State<MarketerMyCompaniesScreen> createState() =>
      _MarketerMyCompaniesScreenState();
}

class _MarketerMyCompaniesScreenState extends State<MarketerMyCompaniesScreen>
    with SingleTickerProviderStateMixin {
  late ApiService _api;
  late Future<Map<String, dynamic>> _future;
  final currency = NumberFormat.simpleCurrency(name: 'NGN', decimalDigits: 0);

  // animation controls
  final List<bool> _visible = [];

  @override
  void initState() {
    super.initState();
    _api = ApiService();
    _reload();
  }

  void _reload() {
    _future = _api.getMarketerMyCompanies(token: widget.token);
    _future.then((data) {
      final companies = (data['companies'] as List?) ?? [];
      _visible.clear();
      _visible.addAll(List<bool>.filled(companies.length, false));
      for (var i = 0; i < companies.length; i++) {
        Future.delayed(Duration(milliseconds: 120 * i), () {
          if (mounted) setState(() => _visible[i] = true);
        });
      }
    }).catchError((_) {});
  }

  Future<void> _refresh() async {
    _reload();
    await _future;
  }

  Color _rankColor(int? pos) {
    if (pos == null) return const Color(0xFFE6EEF6);
    if (pos == 1) return const Color(0xFFFFD700);
    if (pos == 2) return const Color(0xFFC0C0C0);
    if (pos == 3) return const Color(0xFFCD7F32);
    if (pos <= 5) return const Color(0xFF7C5CF6);
    if (pos <= 10) return const Color(0xFF16A34A);
    if (pos <= 20) return const Color(0xFF3B82F6);
    return const Color(0xFFF1F5F9);
  }

  // Rank badge widget (mirrors badges in HTML)
  Widget _rankBadge(int? pos) {
    if (pos == null) return const SizedBox.shrink();
    String label;
    IconData icon = Icons.star;
    Color fg = Colors.white;
    if (pos == 1) {
      label = 'Top #1';
      icon = Icons.emoji_events;
      fg = const Color(0xFF7C5F00);
    } else if (pos == 2) {
      label = 'Top #2';
    } else if (pos == 3) {
      label = 'Top #3';
    } else if (pos <= 5) {
      label = 'Top #$pos';
    } else if (pos <= 10) {
      label = 'Top #$pos';
    } else if (pos <= 20) {
      label = 'Top #$pos';
    } else {
      label = '#$pos';
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: _rankColor(pos),
        borderRadius: BorderRadius.circular(20),
        boxShadow: [
          BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 6)
        ],
      ),
      child: Row(mainAxisSize: MainAxisSize.min, children: [
        Icon(icon, size: 14, color: fg),
        const SizedBox(width: 6),
        Text(label,
            style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.w700, color: fg)),
      ]),
    );
  }

  // Summary card (Companies, Clients, Closed deals)
  Widget _summaryCard(List<dynamic> companies) {
    final totalClients =
        companies.fold<int>(0, (p, e) => p + ((e['client_count'] ?? 0) as int));
    final totalClosed =
        companies.fold<int>(0, (p, e) => p + ((e['closed_deals'] ?? 0) as int));

    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: const Color(0xFFE9ECEF))),
      child: Row(children: [
        _summaryTile(
            'Companies', companies.length.toString(), const Color(0xFF10B981)),
        const SizedBox(width: 12),
        _summaryTile(
            'Total Clients', totalClients.toString(), const Color(0xFF667EEA)),
        const SizedBox(width: 12),
        _summaryTile(
            'Closed Deals', totalClosed.toString(), const Color(0xFF3B82F6)),
      ]),
    );
  }

  Widget _summaryTile(String label, String value, Color color) {
    return Expanded(
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF6C757D),
                fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Text(value,
            style: TextStyle(
                fontSize: 28, color: color, fontWeight: FontWeight.w800)),
      ]),
    );
  }

  Widget _metricRow(String title, double sales, double? target, Color color) {
    final percent =
        (target != null && target > 0) ? (sales / target).clamp(0.0, 2.0) : 0.0;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text(title,
            style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF6C757D),
                fontWeight: FontWeight.w600)),
        Text(target != null ? '${(percent * 100).toStringAsFixed(0)}%' : '—',
            style: TextStyle(
                fontSize: 12, fontWeight: FontWeight.w700, color: color))
      ]),
      const SizedBox(height: 6),
      ClipRRect(
        borderRadius: BorderRadius.circular(6),
        child: LinearProgressIndicator(
          value: percent > 1 ? 1.0 : percent,
          minHeight: 6,
          backgroundColor: const Color(0xFFF1F5F9),
          valueColor: AlwaysStoppedAnimation<Color>(color),
        ),
      ),
      const SizedBox(height: 8),
      Text(
          target != null
              ? '${currency.format(sales)} / ${currency.format(target)}'
              : currency.format(sales),
          style: const TextStyle(fontSize: 12, color: Color(0xFF6C757D))),
    ]);
  }

  Widget _initialCircle(String name) {
    return Container(
      width: 56,
      height: 56,
      decoration: BoxDecoration(
          color: const Color(0xFF667EEA),
          borderRadius: BorderRadius.circular(8)),
      child: Center(
          child: Text(name.toString().substring(0, 1).toUpperCase(),
              style: const TextStyle(
                  color: Colors.white, fontWeight: FontWeight.w700))),
    );
  }

  Widget _buildHeader(String title) {
    return Container(
      color: Colors.white,
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 18),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title,
              style: const TextStyle(
                  fontSize: 26,
                  fontWeight: FontWeight.w700,
                  color: Color(0xFF0B1220))),
          const SizedBox(height: 8),
          Row(children: const [
            Icon(Icons.home, size: 16, color: Color(0xFF6C757D)),
            SizedBox(width: 8),
            Text('Home', style: TextStyle(color: Color(0xFF6C757D))),
            SizedBox(width: 12),
            Icon(Icons.chevron_right, size: 16, color: Color(0xFF6C757D)),
            SizedBox(width: 12),
            Text('My Companies', style: TextStyle(color: Color(0xFF6C757D)))
          ])
        ],
      ),
    );
  }

  Widget _buildLoading() {
    return Column(
      children: List.generate(3, (i) => _skeletonCard()).toList(),
    );
  }

  Widget _skeletonCard() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(12),
          boxShadow: [
            BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8)
          ]),
      child: Row(children: [
        Container(
            width: 48,
            height: 48,
            decoration: BoxDecoration(
                color: const Color(0xFFEFEFF3),
                borderRadius: BorderRadius.circular(8))),
        const SizedBox(width: 12),
        Expanded(
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Container(height: 12, color: const Color(0xFFEFEFF3)),
          const SizedBox(height: 6),
          Container(height: 10, color: const Color(0xFFEFEFF3))
        ]))
      ]),
    );
  }

  Widget _targetMetric(
      String title, double value, double? target, Color color) {
    final percentage =
        (target != null && target > 0) ? (value / target).clamp(0.0, 2.0) : 0.0;
    return Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
        Text(title,
            style: const TextStyle(
                fontSize: 12,
                color: Color(0xFF6C757D),
                fontWeight: FontWeight.w600)),
        Text(target != null ? '${(percentage * 100).toStringAsFixed(0)}%' : '—',
            style: TextStyle(
                fontSize: 12, color: color, fontWeight: FontWeight.w700))
      ]),
      const SizedBox(height: 6),
      Stack(children: [
        Container(
            height: 6,
            width: double.infinity,
            decoration: BoxDecoration(
                color: const Color(0xFFF1F5F9),
                borderRadius: BorderRadius.circular(6))),
        AnimatedContainer(
            duration: const Duration(milliseconds: 700),
            curve: Curves.easeOut,
            height: 6,
            width: percentage > 0
                ? MediaQuery.of(context).size.width *
                    0.6 *
                    (percentage > 1 ? 1 : percentage)
                : 2,
            decoration: BoxDecoration(
                color: color, borderRadius: BorderRadius.circular(6)))
      ]),
      const SizedBox(height: 8),
      Text(
          target != null
              ? '${currency.format(value)} / ${currency.format(target)}'
              : currency.format(value),
          style: const TextStyle(fontSize: 12, color: Color(0xFF6C757D)))
    ]);
  }

  Widget _companyCard(Map<String, dynamic> item, [int index = 0]) {
    final company = Map<String, dynamic>.from(item['company'] ?? {});
    final companyName = company['company_name'] ?? 'Company';
    final logo = company['logo_url']?.toString();
    final location = company['location'] ?? '';
    final closedDeals = item['closed_deals'] ?? 0;
    final commissionRate = item['commission_rate'] ?? 0;
    final hasTx = item['has_transactions'] == true;
    final monthlySales = (item['monthly_sales'] ?? 0).toDouble();
    final quarterlySales = (item['quarterly_sales'] ?? 0).toDouble();
    final yearlySales = (item['total_year_sales'] ?? 0).toDouble();
    final monthlyTarget =
        (item['monthly_target']?['target_amount'] as num?)?.toDouble();
    final quarterlyTarget =
        (item['quarterly_target']?['target_amount'] as num?)?.toDouble();
    final yearlyTarget =
        (item['yearly_target']?['target_amount'] as num?)?.toDouble();
    final rankPos =
        (item['rank_position'] is int) ? item['rank_position'] as int : null;
    final clients = item['client_count'] ?? 0;

    return AnimatedOpacity(
      duration: Duration(milliseconds: 300 + (index * 40)),
      opacity: _visible.length > index ? (_visible[index] ? 1.0 : 0.0) : 0.0,
      child: Transform.translate(
        offset: Offset(
            0, _visible.length > index ? (_visible[index] ? 0 : 12) : 12),
        child: GestureDetector(
          onTap: () {
            Navigator.pushNamed(context, '/marketer-company-portfolio',
                arguments: {'token': widget.token, 'companyId': company['id']});
          },
          child: Container(
            margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
                color: Colors.white,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFE9ECEF)),
                boxShadow: [
                  BoxShadow(
                      color: Colors.black.withOpacity(0.04), blurRadius: 8)
                ]),
            child: Stack(children: [
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Row(crossAxisAlignment: CrossAxisAlignment.center, children: [
                  Hero(
                      tag: 'company-logo-${company['id']}',
                      child: logo != null && logo.isNotEmpty
                          ? ClipRRect(
                              borderRadius: BorderRadius.circular(8),
                              child: Image.network(logo,
                                  width: 56,
                                  height: 56,
                                  fit: BoxFit.cover,
                                  errorBuilder: (_, __, ___) => Container(
                                      width: 56,
                                      height: 56,
                                      decoration: BoxDecoration(
                                          color: const Color(0xFFEFEFF3),
                                          borderRadius:
                                              BorderRadius.circular(8)),
                                      child: Center(
                                          child: Text(companyName
                                              .toString()
                                              .substring(0, 1)
                                              .toUpperCase())))))
                          : Container(
                              width: 56,
                              height: 56,
                              alignment: Alignment.center,
                              decoration: BoxDecoration(
                                  color: const Color(0xFF667EEA),
                                  borderRadius: BorderRadius.circular(8)),
                              child:
                                  Text(companyName.toString().substring(0, 1).toUpperCase(),
                                      style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.w700)))),
                  const SizedBox(width: 12),
                  Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                        Text(companyName.toString(),
                            style: const TextStyle(
                                fontWeight: FontWeight.w700, fontSize: 16)),
                        if (location != null && location.toString().isNotEmpty)
                          Text(location.toString(),
                              style: const TextStyle(
                                  color: Color(0xFF6C757D), fontSize: 12))
                      ])),
                  const SizedBox(width: 8),
                  Column(children: [
                    _rankBadge(rankPos),
                    const SizedBox(height: 6),
                    Text('$clients clients',
                        style: const TextStyle(
                            fontSize: 12, color: Color(0xFF6C757D)))
                  ])
                ]),
                const SizedBox(height: 12),
                Row(children: [
                  _statTile('Closed Deals', closedDeals.toString()),
                  const SizedBox(width: 12),
                  _statTile('Commission', '$commissionRate%')
                ]),
                const SizedBox(height: 12),
                Row(children: [
                  Expanded(
                      child: _metricRow('Monthly', monthlySales, monthlyTarget,
                          const Color(0xFF3B82F6))),
                  const SizedBox(width: 12),
                  Expanded(
                      child: _metricRow('Quarterly', quarterlySales,
                          quarterlyTarget, const Color(0xFF8B5CF6))),
                  const SizedBox(width: 12),
                  Expanded(
                      child: _metricRow('Yearly', yearlySales, yearlyTarget,
                          const Color(0xFF10B981)))
                ]),
                const SizedBox(height: 12),
                Row(mainAxisAlignment: MainAxisAlignment.end, children: [
                  TextButton(
                      onPressed: () => Navigator.pushNamed(
                              context, '/marketer-company-portfolio',
                              arguments: {
                                'token': widget.token,
                                'companyId': company['id']
                              }),
                      style: TextButton.styleFrom(
                          backgroundColor: const Color(0xFF667EEA),
                          padding: const EdgeInsets.symmetric(
                              horizontal: 14, vertical: 12),
                          shape: RoundedRectangleBorder(
                              borderRadius: BorderRadius.circular(8))),
                      child: const Text('View Portfolio',
                          style: TextStyle(color: Colors.white)))
                ])
              ]),
              if (!hasTx)
                Positioned.fill(
                    child: AnimatedOpacity(
                        opacity: 0.88,
                        duration: const Duration(milliseconds: 450),
                        child: Container(
                            decoration: BoxDecoration(
                                color: Colors.white.withOpacity(0.95),
                                borderRadius: BorderRadius.circular(12)),
                            child: Center(
                                child: Column(
                                    mainAxisSize: MainAxisSize.min,
                                    children: const [
                                  Icon(Icons.hourglass_empty,
                                      color: Color(0xFF94A3B8), size: 36),
                                  SizedBox(height: 8),
                                  Text('No transactions yet',
                                      style: TextStyle(
                                          color: Color(0xFF64748B),
                                          fontWeight: FontWeight.w600))
                                ])))))
            ]),
          ),
        ),
      ),
    );
  }

  Widget _statTile(String label, String value) {
    return Expanded(
      child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
          decoration: BoxDecoration(
              color: const Color(0xFFF8FAFC),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: const Color(0xFFE9ECEF))),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(label,
                style: const TextStyle(
                    fontSize: 12,
                    color: Color(0xFF6C757D),
                    fontWeight: FontWeight.w600)),
            const SizedBox(height: 6),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700))
          ])),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: PreferredSize(
          preferredSize: const Size.fromHeight(108),
          child: _buildHeader('My Companies')),
      body: FutureBuilder<Map<String, dynamic>>(
        future: _future,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting)
            return _buildLoading();
          if (snapshot.hasError)
            return Center(child: Text('Error: ${snapshot.error}'));
          final data = snapshot.data ?? {};
          final companies = (data['companies'] as List?) ?? [];
          if (companies.isEmpty) return _buildEmpty();
          return RefreshIndicator(
            onRefresh: _refresh,
            child: ListView.builder(
              physics: const AlwaysScrollableScrollPhysics(),
              itemCount: companies.length,
              itemBuilder: (context, index) =>
                  _companyCard(companies[index] as Map<String, dynamic>, index),
            ),
          );
        },
      ),
    );
  }

  Widget _buildEmpty() {
    return SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(children: [
          const SizedBox(height: 60),
          Container(
              width: 120,
              height: 120,
              decoration: BoxDecoration(
                  color: const Color(0xFFF1F5F9),
                  borderRadius: BorderRadius.circular(20)),
              child: const Icon(Icons.inbox_outlined,
                  size: 56, color: Color(0xFF6C757D))),
          const SizedBox(height: 32),
          Text('No Companies Yet',
              style: Theme.of(context)
                  .textTheme
                  .headlineSmall
                  ?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          Text('You haven\'t been affiliated with any companies yet.',
              textAlign: TextAlign.center,
              style: Theme.of(context)
                  .textTheme
                  .bodyMedium
                  ?.copyWith(color: const Color(0xFF6C757D))),
          const SizedBox(height: 20),
          ElevatedButton(
              onPressed: () => Navigator.pushNamed(
                  context, '/marketer-dashboard', arguments: widget.token),
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF667EEA),
                  padding:
                      const EdgeInsets.symmetric(horizontal: 28, vertical: 12),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(8))),
              child: const Text('Go to Dashboard'))
        ]));
  }
}
