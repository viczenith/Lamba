import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:url_launcher/url_launcher.dart';
import 'package:real_estate_app/core/api_service.dart';

/// A polished, animated, mobile-friendly replica of the
/// `my_company_portfolio.html` page.
///
/// Usage:
/// Navigator.push(context, MaterialPageRoute(
///   builder: (_) => MarketerCompanyPortfolioScreen(
///     companyId: 123,
///     token: '<auth-token>',
///     companyName: 'Acme Estate',
///     companyLogo: 'https://...'
///   )
/// ));
class MarketerCompanyPortfolioScreen extends StatefulWidget {
  final int companyId;
  final String token;
  final String? companyName;
  final String? companyLogo;

  const MarketerCompanyPortfolioScreen({
    Key? key,
    required this.companyId,
    required this.token,
    this.companyName,
    this.companyLogo,
  }) : super(key: key);

  @override
  _MarketerCompanyPortfolioScreenState createState() =>
      _MarketerCompanyPortfolioScreenState();
}

class _MarketerCompanyPortfolioScreenState
    extends State<MarketerCompanyPortfolioScreen>
    with SingleTickerProviderStateMixin {
  bool _loading = true;
  String? _error;
  Map<String, dynamic>? _payload;
  late final NumberFormat _currency;

  // small animation controller for entry animations
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _currency = NumberFormat.currency(symbol: '₦', decimalDigits: 0);
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 700),
    );
    _fetch();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _fetch() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final data = await ApiService().getMarketerCompanyPortfolio(
        companyId: widget.companyId,
        token: widget.token,
      );
      setState(() {
        _payload = data;
        _loading = false;
      });
      _controller.forward();
    } catch (e) {
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  String _fmtCurrency(num? v) {
    if (v == null) return '₦0';
    return _currency.format(v);
  }

  Color _statusColor(String? status) {
    final s = (status ?? '').toLowerCase();
    if (s.contains('paid') || s.contains('complete') || s.contains('fully'))
      return const Color(0xFF10B981); // green
    if (s.contains('pending')) return const Color(0xFFF59E0B); // amber
    return const Color(0xFF64748B); // muted
  }

  String _sanitizePhone(String phone) {
    return phone.replaceAll(RegExp(r'[\s\-\(\)\+]'), '');
  }

  Future<void> _launchWhatsApp(String phone) async {
    final sanitized = _sanitizePhone(phone);
    final uri = Uri.parse('https://wa.me/$sanitized');
    if (await canLaunchUrl(uri)) {
      await launchUrl(uri, mode: LaunchMode.externalApplication);
    }
  }

  Widget _buildHeader() {
    final companyName =
        widget.companyName ?? _payload?['company_name'] ?? 'Company';
    final logo = widget.companyLogo ?? _payload?['company_logo'];
    final clients = (_payload?['clients'] as List?)?.length ?? 0;
    final closedDeals = _payload?['closed_deals'] ?? 0;
    final commissionEarned = _payload?['commission_earned'] ?? 0.0;
    final commissionRate = _payload?['commission_rate'];

    return SliverAppBar(
      pinned: true,
      expandedHeight: 180,
      backgroundColor: const Color(0xFF0F172A),
      leading: IconButton(
        icon: const Icon(Icons.arrow_back, color: Colors.white),
        onPressed: () => Navigator.maybePop(context),
      ),
      flexibleSpace: FlexibleSpaceBar(
        titlePadding: const EdgeInsetsDirectional.only(start: 56, bottom: 12),
        title: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(companyName,
                style:
                    const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
            const SizedBox(height: 2),
            const Text('Client Portfolio',
                style: TextStyle(fontSize: 12, color: Colors.white70)),
          ],
        ),
        background: Container(
          decoration: const BoxDecoration(
            gradient: LinearGradient(
              colors: [Color(0xFF0F172A), Color(0xFF1E293B)],
              begin: Alignment.topLeft,
              end: Alignment.bottomRight,
            ),
          ),
          child: Padding(
            padding: const EdgeInsets.fromLTRB(16, 56, 16, 16),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.center,
              children: [
                Hero(
                  tag: 'company-logo-${widget.companyId}',
                  child: CircleAvatar(
                    radius: 36,
                    backgroundColor: Colors.white24,
                    backgroundImage:
                        (logo != null && logo.toString().isNotEmpty)
                            ? NetworkImage(logo)
                            : null,
                    child: (logo == null || logo.toString().isEmpty)
                        ? Text(
                            (companyName.isNotEmpty ? companyName[0] : '?')
                                .toUpperCase(),
                            style: const TextStyle(
                                fontSize: 20, color: Colors.white),
                          )
                        : null,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('$clients',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 18)),
                          const SizedBox(height: 2),
                          const Text('Clients',
                              style: TextStyle(
                                  color: Colors.white70, fontSize: 12)),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.center,
                        children: [
                          Text('$closedDeals',
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 18)),
                          const SizedBox(height: 2),
                          const Text('Closed Deals',
                              style: TextStyle(
                                  color: Colors.white70, fontSize: 12)),
                        ],
                      ),
                      Column(
                        crossAxisAlignment: CrossAxisAlignment.end,
                        children: [
                          Text(_fmtCurrency(commissionEarned),
                              style: const TextStyle(
                                  color: Colors.white,
                                  fontWeight: FontWeight.w700,
                                  fontSize: 18)),
                          const SizedBox(height: 2),
                          Text(
                              'Commission (${commissionRate?.toStringAsFixed(1) ?? '0'}%)',
                              style: const TextStyle(
                                  color: Colors.white70, fontSize: 12)),
                        ],
                      ),
                    ],
                  ),
                )
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildLeaderboardCard() {
    final List<dynamic> top3 = _payload?['top3'] ?? [];
    final Map<String, dynamic>? userEntry = (_payload?['user_entry'] is Map)
        ? Map<String, dynamic>.from(_payload!['user_entry'])
        : null;
    final currentYear = _payload?['current_year'] ?? DateTime.now().year;

    return SliverToBoxAdapter(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Card(
          shape:
              RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          elevation: 6,
          child: ExpansionTile(
            initiallyExpanded: false,
            tilePadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            childrenPadding:
                const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            leading: const Icon(Icons.emoji_events_rounded,
                color: Color(0xFFFBBF24)),
            title: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Top 3 Performers of the Year',
                    style: TextStyle(fontWeight: FontWeight.w700)),
                Chip(
                  label: Text('$currentYear',
                      style: const TextStyle(
                          color: Colors.white, fontWeight: FontWeight.w600)),
                  backgroundColor: const Color(0xFF1E293B),
                )
              ],
            ),
            children: [
              if (top3.isEmpty) ...[
                const SizedBox(height: 8),
                Center(
                    child: Text('No performers yet',
                        style: TextStyle(color: Colors.grey[600]))),
                const SizedBox(height: 8),
              ] else ...[
                Column(
                  children: top3.map<Widget>((entry) {
                    final rank = entry['rank'] ?? 0;
                    final marketer = entry['marketer'] ?? {};
                    final name =
                        marketer['full_name'] ?? marketer['name'] ?? '—';
                    final profile = marketer['profile_image'];
                    final isGold = rank == 1;
                    final isSilver = rank == 2;
                    final isBronze = rank == 3;

                    return Container(
                      margin: const EdgeInsets.symmetric(vertical: 6),
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: rank == 1 ? const Color(0xFFFDF7E6) : null,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: Row(
                        children: [
                          Container(
                            width: 40,
                            height: 40,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: const Color(0xFF0F172A),
                            ),
                            child: Center(
                              child: Text('#$rank',
                                  style: const TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w700)),
                            ),
                          ),
                          const SizedBox(width: 12),
                          CircleAvatar(
                            radius: 18,
                            backgroundImage: (profile != null &&
                                    profile.toString().isNotEmpty)
                                ? NetworkImage(profile)
                                : null,
                            child: (profile == null ||
                                    profile.toString().isEmpty)
                                ? Text(
                                    (name as String)
                                        .substring(0, 1)
                                        .toUpperCase(),
                                    style: const TextStyle(color: Colors.white))
                                : null,
                            backgroundColor: const Color(0xFF60A5FA),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                              child: Text(name,
                                  style: const TextStyle(
                                      fontWeight: FontWeight.w600))),
                          if (isGold)
                            const Icon(Icons.emoji_events,
                                color: Color(0xFFF59E0B))
                          else if (isSilver)
                            const Icon(Icons.emoji_events,
                                color: Color(0xFF94A3B8))
                          else if (isBronze)
                            const Icon(Icons.emoji_events,
                                color: Color(0xFFEA580C))
                        ],
                      ),
                    );
                  }).toList(),
                ),
                if (userEntry != null) ...[
                  const Divider(height: 20),
                  Row(
                    children: [
                      Expanded(
                          child: Text('Your Position',
                              style: TextStyle(
                                  color: Colors.grey[700],
                                  fontWeight: FontWeight.w700))),
                      Text('#${userEntry['rank'] ?? '—'}',
                          style: const TextStyle(fontWeight: FontWeight.w700)),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                        color: const Color(0xFFF3F4F6),
                        borderRadius: BorderRadius.circular(8)),
                    child: Row(
                      children: [
                        CircleAvatar(
                          backgroundImage:
                              (userEntry['marketer']?['profile_image'] != null)
                                  ? NetworkImage(
                                      userEntry['marketer']!['profile_image'])
                                  : null,
                          child: (userEntry['marketer']?['profile_image'] ==
                                  null)
                              ? Text(
                                  (userEntry['marketer']?['full_name'] ?? '?')
                                      .toString()
                                      .substring(0, 1)
                                      .toUpperCase())
                              : null,
                        ),
                        const SizedBox(width: 12),
                        Expanded(
                            child: Text(
                                userEntry['marketer']?['full_name'] ?? 'You',
                                style: const TextStyle(
                                    fontWeight: FontWeight.w600))),
                        const SizedBox(width: 8),
                        Text('You',
                            style: TextStyle(
                                color: Colors.blue[700],
                                fontWeight: FontWeight.w700)),
                      ],
                    ),
                  )
                ]
              ]
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildClientsList() {
    final List<dynamic> clients = _payload?['clients'] ?? [];

    if (clients.isEmpty) {
      return SliverToBoxAdapter(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.inbox, size: 56, color: Color(0xFF94A3B8)),
              const SizedBox(height: 12),
              const Text('No Clients Yet',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700)),
              const SizedBox(height: 6),
              Text("You haven't handled any clients for this company.",
                  style: TextStyle(color: Colors.grey[600])),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                onPressed: () => Navigator.maybePop(context),
                icon: const Icon(Icons.arrow_back),
                label: const Text('Back to Companies'),
              )
            ],
          ),
        ),
      );
    }

    return SliverList(
      delegate: SliverChildBuilderDelegate((context, index) {
        final client = Map<String, dynamic>.from(clients[index] as Map);
        return _ClientCard(
          client: client,
          currencyFmt: _fmtCurrency,
          onWhatsApp: (phone) => _launchWhatsApp(phone),
          statusColor: _statusColor,
        );
      }, childCount: clients.length),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      body: SafeArea(
        bottom: false,
        child: _loading
            ? Center(
                child: CircularProgressIndicator(
                    valueColor:
                        AlwaysStoppedAnimation(const Color(0xFF0F172A))))
            : _error != null
                ? Center(child: Text(_error!))
                : RefreshIndicator(
                    onRefresh: _fetch,
                    child: CustomScrollView(
                      physics: const AlwaysScrollableScrollPhysics(),
                      slivers: [
                        _buildHeader(),
                        _buildLeaderboardCard(),
                        SliverToBoxAdapter(
                          child: Padding(
                            padding: const EdgeInsets.symmetric(
                                horizontal: 16, vertical: 8),
                            child: Row(
                              children: [
                                const Icon(Icons.people_outline,
                                    color: Color(0xFF0F172A)),
                                const SizedBox(width: 8),
                                Text('Your Clients',
                                    style: TextStyle(
                                        fontWeight: FontWeight.w700,
                                        color: Colors.grey[900])),
                                const Spacer(),
                                Text(
                                    '${(_payload?['clients'] as List?)?.length ?? 0}',
                                    style: const TextStyle(
                                        fontWeight: FontWeight.w700)),
                              ],
                            ),
                          ),
                        ),
                        _buildClientsList(),
                        const SliverToBoxAdapter(child: SizedBox(height: 48)),
                      ],
                    ),
                  ),
      ),
    );
  }
}

class _ClientCard extends StatefulWidget {
  final Map<String, dynamic> client;
  final String Function(num? v) currencyFmt;
  final void Function(String phone) onWhatsApp;
  final Color Function(String? status) statusColor;

  const _ClientCard({
    Key? key,
    required this.client,
    required this.currencyFmt,
    required this.onWhatsApp,
    required this.statusColor,
  }) : super(key: key);

  @override
  State<_ClientCard> createState() => _ClientCardState();
}

class _ClientCardState extends State<_ClientCard> {
  final DateFormat _dateFmt = DateFormat('MMM d, y');
  final Duration _animDuration = const Duration(milliseconds: 350);

  Map<String, List<Map<String, dynamic>>> _groupTransactions(
      List<dynamic>? txs) {
    final Map<String, List<Map<String, dynamic>>> groups = {};
    if (txs == null) return groups;
    for (final tx in txs) {
      final Map<String, dynamic> t = Map<String, dynamic>.from(tx as Map);
      final estateName =
          (t['allocation']?['estate']?['name'] ?? 'Other').toString();
      groups.putIfAbsent(estateName, () => []).add(t);
    }
    return groups;
  }

  @override
  Widget build(BuildContext context) {
    final c = widget.client;
    final fullName = c['full_name'] ?? '—';
    final phone = c['phone_number'] ?? '';
    final email = c['email'];
    final address = c['address'];
    final dateRegistered = c['date_registered'];
    final profile = c['profile_image'];
    final txs = (c['company_transactions'] as List?) ?? [];

    final groups = _groupTransactions(txs);

    return AnimatedContainer(
      duration: _animDuration,
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.04),
              blurRadius: 8,
              offset: const Offset(0, 4))
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // header
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 12),
            child: Row(
              children: [
                CircleAvatar(
                  radius: 26,
                  backgroundImage:
                      (profile != null && profile.toString().isNotEmpty)
                          ? NetworkImage(profile)
                          : null,
                  child: (profile == null || profile.toString().isEmpty)
                      ? Text((fullName as String).substring(0, 1).toUpperCase(),
                          style: const TextStyle(color: Colors.white))
                      : null,
                  backgroundColor: const Color(0xFF60A5FA),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(fullName,
                          style: const TextStyle(
                              fontWeight: FontWeight.w700, fontSize: 16)),
                      const SizedBox(height: 4),
                      Text(phone, style: TextStyle(color: Colors.grey[600])),
                    ],
                  ),
                ),
                IconButton(
                  onPressed: () => widget.onWhatsApp(phone.toString()),
                  icon: const Icon(Icons.message, color: Color(0xFF25D366)),
                )
              ],
            ),
          ),

          // meta
          Container(
            color: const Color(0xFFF8FAFC),
            padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
            child: Row(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      const Icon(Icons.email_outlined,
                          size: 16, color: Color(0xFF94A3B8)),
                      const SizedBox(width: 8),
                      Expanded(
                          child: Text(email ?? '—',
                              style: const TextStyle(fontSize: 13))),
                    ],
                  ),
                ),
                Expanded(
                  child: Row(
                    children: [
                      const Icon(Icons.location_on_outlined,
                          size: 16, color: Color(0xFF94A3B8)),
                      const SizedBox(width: 8),
                      Expanded(
                          child: Text(address ?? 'Not provided',
                              style: const TextStyle(fontSize: 13))),
                    ],
                  ),
                ),
                Expanded(
                  child: Row(
                    children: [
                      const Icon(Icons.calendar_today_outlined,
                          size: 16, color: Color(0xFF94A3B8)),
                      const SizedBox(width: 8),
                      Expanded(
                          child: Text(
                              dateRegistered != null
                                  ? _dateFmt
                                      .format(DateTime.parse(dateRegistered))
                                  : '—',
                              style: const TextStyle(fontSize: 13))),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // transactions
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
            child: Column(
              children: groups.keys.map((estateName) {
                final items = groups[estateName]!;
                return Container(
                  margin: const EdgeInsets.symmetric(vertical: 6),
                  decoration: BoxDecoration(
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: const Color(0xFFE6EEF6))),
                  child: ExpansionTile(
                    initiallyExpanded: true,
                    title: Row(
                      children: [
                        Expanded(
                            child: Text(estateName,
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700))),
                        Text(
                            '${items.length} plot${items.length > 1 ? 's' : ''}',
                            style: TextStyle(color: Colors.grey[600])),
                      ],
                    ),
                    children: items.map((txn) {
                      final amount =
                          txn['amount'] ?? txn['total_amount'] ?? 0.0;
                      final status = (txn['status'] ?? '').toString();
                      final allocated =
                          (txn['allocation']?['plot_number'] ?? null) != null;
                      final plotSize =
                          txn['allocation']?['plot_size']?['size'] ?? '';

                      return ListTile(
                        dense: true,
                        title: Row(
                          children: [
                            Text(plotSize.toString(),
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700)),
                            const SizedBox(width: 8),
                            Text(widget.currencyFmt(amount as num?),
                                style: const TextStyle(
                                    fontWeight: FontWeight.w700)),
                          ],
                        ),
                        subtitle: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.symmetric(
                                  horizontal: 8, vertical: 4),
                              decoration: BoxDecoration(
                                  color: widget
                                      .statusColor(status)
                                      .withOpacity(0.12),
                                  borderRadius: BorderRadius.circular(6)),
                              child: Text(status,
                                  style: TextStyle(
                                      color: widget.statusColor(status),
                                      fontWeight: FontWeight.w700,
                                      fontSize: 12)),
                            ),
                            const SizedBox(width: 8),
                            Text(allocated ? 'Allocated' : 'Pending',
                                style: TextStyle(
                                    color: allocated
                                        ? const Color(0xFF10B981)
                                        : const Color(0xFFEF4444),
                                    fontWeight: FontWeight.w700,
                                    fontSize: 12)),
                            const SizedBox(width: 12),
                            Text(
                                txn['transaction_date'] != null
                                    ? _dateFmt.format(
                                        DateTime.parse(txn['transaction_date']))
                                    : '',
                                style: TextStyle(color: Colors.grey[600])),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
                );
              }).toList(),
            ),
          ),
        ],
      ),
    );
  }
}
