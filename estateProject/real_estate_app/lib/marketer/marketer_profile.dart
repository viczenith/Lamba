import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:real_estate_app/shared/app_side.dart';
import 'package:shimmer/shimmer.dart';
import 'package:real_estate_app/core/api_service.dart';
import 'package:real_estate_app/shared/app_layout.dart';
import 'package:real_estate_app/marketer/marketer_bottom_nav.dart';

class MarketerProfile extends StatefulWidget {
  final String token;

  const MarketerProfile({Key? key, required this.token}) : super(key: key);

  @override
  _MarketerProfileState createState() => _MarketerProfileState();
}

class _MarketerProfileState extends State<MarketerProfile>
    with TickerProviderStateMixin {
  String? _headerImageUrl;
  late final AnimationController _glowController;
  final Map<int, NumberFormat> _currencyFormatCache = {};
  bool _currentVisible = false;
  bool _newVisible = false;
  bool _confirmVisible = false;

  late TabController _tabController;
  late Future<Map<String, dynamic>> _profileFuture;

  final ImagePicker _picker = ImagePicker();
  File? _imageFile;

  // profile cache used across tabs
  Map<String, dynamic> _profileData = {};

  final _formKey = GlobalKey<FormState>();
  final _passwordFormKey = GlobalKey<FormState>();

  final TextEditingController _companyController = TextEditingController();
  final TextEditingController _jobController = TextEditingController();
  final TextEditingController _fullNameController = TextEditingController();
  final TextEditingController _aboutController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _addressController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();

  final TextEditingController _currentPasswordController =
      TextEditingController();
  final TextEditingController _newPasswordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  // ---------------- util/parsers ----------------
  double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is String) {
      final cleaned = v.replaceAll(',', '');
      return double.tryParse(cleaned) ?? 0.0;
    }
    try {
      return double.parse(v.toString());
    } catch (_) {
      return 0.0;
    }
  }

  int _toInt(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v;
    if (v is double) return v.toInt();
    if (v is String) {
      final s = v.replaceAll(',', '').trim();
      return int.tryParse(s) ?? (double.tryParse(s)?.toInt() ?? 0);
    }
    try {
      return int.parse(v.toString());
    } catch (_) {
      try {
        return (double.parse(v.toString())).toInt();
      } catch (_) {
        return 0;
      }
    }
  }

  /// Returns a normalized dashboard summary map using canonical keys:
  /// { total_transactions, number_clients, total_companies }
  Map<String, dynamic> _getDashboardSummary(Map<String, dynamic>? profile) {
    if (profile == null) return <String, dynamic>{};
    // prefer explicit canonical shape
    if (profile['dashboard_summary'] is Map<String, dynamic>) {
      return Map<String, dynamic>.from(profile['dashboard_summary'] as Map);
    }

    // accept several legacy/name variants
    final candidate = <String, dynamic>{
      'total_transactions': profile['total_transactions'] ??
          profile['total_tx'] ??
          profile['tx_count'] ??
          profile['performance']?['total_transactions'],
      'number_clients': profile['number_clients'] ??
          profile['clients_count'] ??
          profile['performance']?['clients_count'],
      'total_companies': profile['total_companies'] ??
          profile['companies_count'] ??
          profile['total_estates_sold'],
    };

    // coerce to ints
    return {
      'total_transactions': _toInt(candidate['total_transactions']),
      'number_clients': _toInt(candidate['number_clients']),
      'total_companies': _toInt(candidate['total_companies']),
    };
  }

  /// Normalize `companies[]` or legacy parallel arrays into a predictable list
  List<Map<String, dynamic>>? _normalizeCompaniesFromProfile(
      Map<String, dynamic>? p) {
    if (p == null) return null;
    if (p['companies'] is List) {
      return (p['companies'] as List)
          .whereType<Map<String, dynamic>>()
          .map((e) {
        return {
          'company_id': e['company_id'] ?? e['id'],
          'company_name': e['company_name'] ?? e['name'] ?? '',
          'transactions': _toInt(e['transactions'] ?? e['tx'] ?? e['count']),
          'company_logo': e['company_logo'] ?? e['logo'] ?? null,
        };
      }).toList();
    }

    if (p['company_names'] is List && p['company_transactions'] is List) {
      final names =
          (p['company_names'] as List).map((e) => e?.toString() ?? '').toList();
      final txs =
          (p['company_transactions'] as List).map((e) => _toInt(e)).toList();
      final n = names.length < txs.length ? names.length : txs.length;
      final out = <Map<String, dynamic>>[];
      for (var i = 0; i < n; i++) {
        out.add({
          'company_id': null,
          'company_name': names[i],
          'transactions': txs[i],
          'company_logo': null
        });
      }
      return out;
    }

    return null;
  }

  String formatCurrency(dynamic valueOrDouble,
      {int? decimalDigits, String locale = 'en_NG'}) {
    final double value =
        valueOrDouble is double ? valueOrDouble : _toDouble(valueOrDouble);
    final digits = decimalDigits ?? (value.abs() >= 1000 ? 0 : 2);

    final fmt = _currencyFormatCache.putIfAbsent(digits, () {
      return NumberFormat.currency(
        locale: locale,
        symbol: '\u20A6',
        decimalDigits: digits,
      );
    });

    try {
      return fmt.format(value);
    } catch (_) {
      return '\u20A6${value.toStringAsFixed(digits)}';
    }
  }

  // ---------------- lifecycle ----------------
  @override
  void initState() {
    super.initState();
    // Reduced tabs to match server-rendered HTML: Details, Edit Profile, Password
    _tabController = TabController(length: 3, vsync: this);

    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _loadProfile();
  }

  void _loadProfile() {
    _profileFuture = ApiService()
        .getMarketerProfileByToken(token: widget.token)
        .then((data) {
      // hydrate header and cache
      final maybeHeader = (data['header_image'] ?? data['profile_image']);
      if (maybeHeader is String && maybeHeader.isNotEmpty) {
        _headerImageUrl = maybeHeader;
      }
      _profileData = Map<String, dynamic>.from(data);
      // prefill controllers
      _companyController.text = _profileData['company'] ?? '';
      _jobController.text = _profileData['job'] ?? '';
      _fullNameController.text = _profileData['full_name'] ?? '';
      _aboutController.text = _profileData['about'] ?? '';
      _countryController.text = _profileData['country'] ?? '';
      _addressController.text = _profileData['address'] ?? '';
      _phoneController.text = _profileData['phone'] ?? '';
      _emailController.text = _profileData['email'] ?? '';

      // normalize canonical dashboard_summary and companies[] (server may return legacy shapes)
      final ds = _getDashboardSummary(_profileData);
      if (ds.isNotEmpty) _profileData['dashboard_summary'] = ds;
      final comps = _normalizeCompaniesFromProfile(_profileData);
      if (comps != null) _profileData['companies'] = comps;

      return data;
    });
  }

  @override
  void dispose() {
    _companyController.dispose();
    _jobController.dispose();
    _tabController.dispose();
    _glowController.dispose();
    _fullNameController.dispose();
    _aboutController.dispose();
    _countryController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  // ---------------- image & API interactions ----------------
  Future<void> _pickImage() async {
    final picked = await _picker.pickImage(source: ImageSource.gallery);
    if (!mounted) return;
    if (picked != null) {
      setState(() => _imageFile = File(picked.path));
    }
  }

  Future<void> _submitProfileUpdate() async {
    // According to DRF view: allowed updatable fields: about, company, job, country, profile_image
    if (!_formKey.currentState!.validate()) return;

    try {
      final updated = await ApiService().updateMarketerProfileDetails(
        token: widget.token,
        company: _companyController.text,
        job: _jobController.text,
        about: _aboutController.text,
        country: _countryController.text,
        profileImage: _imageFile,
      );

      if (!mounted) return;
      // update local state
      setState(() {
        _profileData = Map<String, dynamic>.from(updated);
        _imageFile = null;
        final maybeHeader =
            (updated['header_image'] ?? updated['profile_image']);
        if (maybeHeader is String && maybeHeader.isNotEmpty)
          _headerImageUrl = maybeHeader;
      });

      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Profile updated successfully',
            style: GoogleFonts.sora(color: Colors.white)),
        backgroundColor: Colors.green,
      ));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Error updating profile: $e',
            style: GoogleFonts.sora(color: Colors.white)),
        backgroundColor: Colors.red,
      ));
    }
  }

  Future<void> _submitPasswordChange() async {
    if (!_passwordFormKey.currentState!.validate()) return;

    if (_newPasswordController.text != _confirmPasswordController.text) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Passwords do not match',
            style: GoogleFonts.sora(color: Colors.white)),
        backgroundColor: Colors.red,
      ));
      return;
    }

    try {
      await ApiService().changeMarketerPassword(
        token: widget.token,
        currentPassword: _currentPasswordController.text,
        newPassword: _newPasswordController.text,
      );

      if (!mounted) return;
      _currentPasswordController.clear();
      _newPasswordController.clear();
      _confirmPasswordController.clear();

      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Password updated successfully',
            style: GoogleFonts.sora(color: Colors.white)),
        backgroundColor: Colors.green,
      ));
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(
        content: Text('Error changing password: $e',
            style: GoogleFonts.sora(color: Colors.white)),
        backgroundColor: Colors.red,
      ));
    }
  }

  Future<void> _refreshProfile() async {
    try {
      final data =
          await ApiService().getMarketerProfileByToken(token: widget.token);
      if (!mounted) return;
      // update UI in one setState
      setState(() {
        _profileData = Map<String, dynamic>.from(data);
        _profileFuture = Future.value(data);

        // update header image if present
        final maybeHeader = (data['header_image'] ?? data['profile_image']);
        if (maybeHeader is String && maybeHeader.isNotEmpty) {
          _headerImageUrl = maybeHeader;
        } else {
          _headerImageUrl = null;
        }

        // Prefill controllers exactly as done in _loadProfile
        _companyController.text = _profileData['company'] ?? '';
        _jobController.text = _profileData['job'] ?? '';
        _fullNameController.text = _profileData['full_name'] ?? '';
        _aboutController.text = _profileData['about'] ?? '';
        _countryController.text = _profileData['country'] ?? '';
        _addressController.text = _profileData['address'] ?? '';
        _phoneController.text = _profileData['phone'] ?? '';
        _emailController.text = _profileData['email'] ?? '';

        // normalize dashboard summary + companies so the Performance tab can read them
        final ds = _getDashboardSummary(_profileData);
        if (ds.isNotEmpty) _profileData['dashboard_summary'] = ds;
        final comps = _normalizeCompaniesFromProfile(_profileData);
        if (comps != null) _profileData['companies'] = comps;

        // Clear any picked-but-not-saved image preview (optional)
        _imageFile = null;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to refresh: $e')),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppLayout(
      pageTitle: 'Profile',
      token: widget.token,
      side: AppSide.marketer,
      child: AnnotatedRegion<SystemUiOverlayStyle>(
        value: SystemUiOverlayStyle.light.copyWith(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
        ),
        child: Scaffold(
          extendBodyBehindAppBar: true,
          backgroundColor: Colors.transparent,
          bottomNavigationBar: MarketerBottomNav(
              currentIndex: 1, token: widget.token, chatBadge: 0),
          body: NestedScrollView(
            floatHeaderSlivers: true,
            headerSliverBuilder: (context, innerBoxIsScrolled) {
              final double topPadding = MediaQuery.of(context).padding.top;
              final double expandedHeight = 280.0 + topPadding;

              return [
                SliverAppBar(
                  backgroundColor: Colors.transparent,
                  surfaceTintColor: Colors.transparent,
                  shadowColor: Colors.transparent,
                  elevation: 0,
                  pinned: true,
                  stretch: true,
                  expandedHeight: expandedHeight,
                  automaticallyImplyLeading: false,
                  centerTitle: false,
                  toolbarHeight: kToolbarHeight + topPadding,
                  collapsedHeight: kToolbarHeight + topPadding,
                  flexibleSpace: LayoutBuilder(builder: (context, constraints) {
                    final double maxHeight = constraints.maxHeight;
                    final double t = ((maxHeight -
                                (kToolbarHeight + topPadding)) /
                            (expandedHeight - (kToolbarHeight + topPadding)))
                        .clamp(0.0, 1.0);

                    const double avatarMax = 110.0;
                    const double avatarMin = 40.0;
                    final double avatarSize =
                        avatarMin + (avatarMax - avatarMin) * t;

                    final double screenWidth =
                        MediaQuery.of(context).size.width;
                    final double avatarCenterLeftExpanded =
                        (screenWidth / 2) - (avatarSize / 2);
                    final double avatarLeftCollapsed = 12.0;
                    final double avatarLeft = avatarLeftCollapsed +
                        (avatarCenterLeftExpanded - avatarLeftCollapsed) * t;

                    final double avatarTopExpanded =
                        expandedHeight - avatarSize / 2 - 16;
                    final double avatarTopCollapsed =
                        MediaQuery.of(context).padding.top +
                            (kToolbarHeight - avatarMin) / 2;
                    final double avatarTop = avatarTopCollapsed +
                        (avatarTopExpanded - avatarTopCollapsed) * t;

                    final double bigTitleOpacity = t;
                    final double smallTitleOpacity = 1.0 - t;
                    final double smallTitleLeftCollapsed =
                        avatarLeftCollapsed + avatarMin + 12.0;
                    final double smallTitleLeftExpanded = 20.0;
                    final double smallTitleLeft = smallTitleLeftCollapsed +
                        (smallTitleLeftExpanded - smallTitleLeftCollapsed) * t;

                    final Widget backgroundImageWidget = (_headerImageUrl !=
                                null &&
                            _headerImageUrl!.isNotEmpty)
                        ? Image.network(
                            _headerImageUrl!,
                            fit: BoxFit.cover,
                            width: double.infinity,
                            height: double.infinity,
                            loadingBuilder: (c, child, progress) {
                              if (progress == null) return child;
                              return Container(color: Colors.grey[300]);
                            },
                            errorBuilder: (c, e, s) => Image.asset(
                                'assets/avater.webp',
                                fit: BoxFit.cover),
                          )
                        : Image.asset('assets/avater.webp', fit: BoxFit.cover);

                    final double glowScale =
                        0.85 + (_glowController.value) * (1.35 - 0.85);
                    final double glowFactor = glowScale * (0.7 + 0.3 * t);

                    return Stack(
                      fit: StackFit.expand,
                      children: [
                        Positioned.fill(child: backgroundImageWidget),
                        Positioned.fill(
                          child: Container(
                            decoration: BoxDecoration(
                              gradient: LinearGradient(
                                colors: [
                                  Colors.black.withOpacity(0.36),
                                  Colors.black.withOpacity(0.08),
                                ],
                                begin: Alignment.topCenter,
                                end: Alignment.bottomCenter,
                              ),
                            ),
                          ),
                        ),
                        Positioned(
                          left: 20,
                          bottom: 20,
                          child: Opacity(
                            opacity: bigTitleOpacity,
                            child: Text(
                              'Profile',
                              style: GoogleFonts.sora(
                                color: Colors.white,
                                fontSize: 28,
                                fontWeight: FontWeight.w700,
                                shadows: [
                                  Shadow(
                                    blurRadius: 6.0,
                                    color: Colors.black.withOpacity(0.45),
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),
                        Positioned(
                          left: smallTitleLeft,
                          top: MediaQuery.of(context).padding.top + 12,
                          child: Opacity(
                            opacity: smallTitleOpacity,
                            child: Text(
                              'Profile',
                              style: GoogleFonts.sora(
                                color: Colors.white,
                                fontSize: 18,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                          ),
                        ),
                        Positioned(
                          left: avatarLeft,
                          top: avatarTop,
                          child: Container(
                            width: avatarSize,
                            height: avatarSize,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              boxShadow: [
                                BoxShadow(
                                  color: const Color(0xFF4154F1)
                                      .withOpacity(0.23 * glowFactor),
                                  blurRadius: 12.0 * glowFactor,
                                  spreadRadius: 1.5 * (glowFactor - 0.9),
                                  offset: Offset(0, 6 * (1.0 - t) + 2),
                                ),
                                BoxShadow(
                                  color: Colors.black.withOpacity(0.14 * t),
                                  blurRadius: 8.0,
                                  offset: const Offset(0, 4),
                                ),
                              ],
                              border: Border.all(
                                color: Colors.white.withOpacity(0.95),
                                width: 3.0,
                              ),
                            ),
                            child: ClipOval(
                              child: Material(
                                color: Colors.transparent,
                                child: InkWell(
                                  onTap: () {},
                                  child: Hero(
                                    tag: 'profile-image',
                                    child: (_headerImageUrl != null &&
                                            _headerImageUrl!.isNotEmpty)
                                        ? Image.network(
                                            _headerImageUrl!,
                                            fit: BoxFit.cover,
                                            width: avatarSize,
                                            height: avatarSize,
                                            loadingBuilder:
                                                (c, child, progress) {
                                              if (progress == null)
                                                return child;
                                              return Container(
                                                  color: Colors.grey[300]);
                                            },
                                            errorBuilder: (c, e, s) =>
                                                Image.asset(
                                              'assets/avater.webp',
                                              fit: BoxFit.cover,
                                            ),
                                          )
                                        : Image.asset(
                                            'assets/avater.webp',
                                            fit: BoxFit.cover,
                                          ),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  }),
                ),
                SliverPersistentHeader(
                  pinned: true,
                  delegate: _SliverAppBarDelegate(
                    TabBar(
                      controller: _tabController,
                      isScrollable: true,
                      indicatorColor: const Color(0xFF4154F1),
                      indicatorWeight: 3.0,
                      labelStyle: GoogleFonts.sora(
                        fontWeight: FontWeight.w600,
                        fontSize: 14.0,
                      ),
                      unselectedLabelStyle: GoogleFonts.sora(
                        fontWeight: FontWeight.w500,
                        fontSize: 14.0,
                      ),
                      tabs: const [
                        Tab(text: 'Details'),
                        Tab(text: 'Edit Profile'),
                        Tab(text: 'Password'),
                      ],
                    ),
                  ),
                ),
              ];
            },
            body: TabBarView(
              controller: _tabController,
              children: [
                _detailsTab(),
                _editProfileTab(),
                _passwordTab(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  // ---------------- Tab: Details ----------------
  Widget _detailsTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _profileFuture,
      builder: (context, snap) {
        if (snap.connectionState == ConnectionState.waiting) {
          return _buildShimmerLoader();
        }
        if (snap.hasError) {
          return Center(child: Text('Error: ${snap.error}'));
        }
        final profile = snap.data!;
        if (_profileData.isEmpty)
          _profileData = Map<String, dynamic>.from(profile);

        return RefreshIndicator(
          onRefresh: _refreshProfile,
          child: CustomScrollView(
            physics: const AlwaysScrollableScrollPhysics(),
            slivers: [
              SliverToBoxAdapter(
                child: Padding(
                  padding: const EdgeInsets.all(16.0),
                  child: Column(
                    children: [
                      _buildProfileCard(profile),
                      const SizedBox(height: 12),
                      _buildProfileDetails(profile),
                      const SizedBox(height: 12),
                      _buildContactInfoCard(profile),
                    ],
                  ),
                ),
              ),
            ],
          ),
        );
      },
    );
  }

  // ---------------- Edit Profile Tab ----------------
  Widget _editProfileTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _profileFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting)
          return _buildShimmerLoader();
        if (snapshot.hasError)
          return Center(child: Text('Error: ${snapshot.error}'));

        final profile = snapshot.data!;
        // ensure controller text (prefill done in _loadProfile but double-check)
        _companyController.text = profile['company'] ?? _companyController.text;
        _jobController.text = profile['job'] ?? _jobController.text;
        _fullNameController.text =
            profile['full_name'] ?? _fullNameController.text;
        _aboutController.text = profile['about'] ?? _aboutController.text;
        _countryController.text = profile['country'] ?? _countryController.text;
        _addressController.text = profile['address'] ?? _addressController.text;
        _phoneController.text = profile['phone'] ?? _phoneController.text;
        _emailController.text = profile['email'] ?? _emailController.text;

        Widget _input({
          required TextEditingController controller,
          required String label,
          required IconData icon,
          bool enabled = true,
          TextInputType? keyboardType,
          int maxLines = 1,
          Widget? suffix,
          String? hint,
          String? Function(String?)? validator,
        }) {
          final fill = enabled ? Colors.white : Colors.grey.shade50;
          final textColor = enabled ? null : Colors.grey.shade700;
          return TextFormField(
            controller: controller,
            enabled: enabled,
            readOnly: !enabled,
            keyboardType: keyboardType,
            maxLines: maxLines,
            style: GoogleFonts.sora(color: textColor),
            validator: (v) {
              if (!enabled) return null;
              if (validator != null) return validator(v);
              return null;
            },
            decoration: InputDecoration(
              labelText: label,
              hintText: hint,
              prefixIcon: Icon(icon, color: Colors.grey.shade600),
              suffixIcon: suffix,
              filled: true,
              fillColor: fill,
              isDense: true,
              contentPadding:
                  const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
              enabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: Colors.grey.withOpacity(0.12)),
              ),
              focusedBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide:
                    const BorderSide(color: Color(0xFF4154F1), width: 1.4),
              ),
              disabledBorder: OutlineInputBorder(
                borderRadius: BorderRadius.circular(12),
                borderSide: BorderSide(color: Colors.grey.withOpacity(0.06)),
              ),
            ),
          );
        }

        return Container(
          color: Colors.white,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
            child:
                Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              // Header card
              Container(
                width: double.infinity,
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(14),
                  boxShadow: [
                    BoxShadow(
                        color: Colors.black.withOpacity(0.04),
                        blurRadius: 18,
                        offset: const Offset(0, 10))
                  ],
                  border: Border.all(color: Colors.grey.withOpacity(0.06)),
                ),
                child: Row(children: [
                  Stack(alignment: Alignment.bottomRight, children: [
                    CircleAvatar(
                      radius: 48,
                      backgroundColor: Colors.grey.shade100,
                      backgroundImage: _imageFile != null
                          ? FileImage(_imageFile!)
                          : (profile['profile_image'] != null
                              ? NetworkImage(profile['profile_image'] as String)
                              : const AssetImage(
                                  'assets/avater.webp')) as ImageProvider,
                    ),
                    Container(
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                            colors: [Color(0xFF4154F1), Color(0xFF6C7BFF)]),
                        shape: BoxShape.circle,
                        border: Border.all(color: Colors.white, width: 2),
                      ),
                      child: IconButton(
                        icon: const Icon(Icons.camera_alt,
                            color: Colors.white, size: 18),
                        onPressed: _pickImage,
                        tooltip: 'Change profile picture',
                      ),
                    ),
                  ]),
                  const SizedBox(width: 16),
                  Expanded(
                      child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                        Text(
                            _fullNameController.text.isNotEmpty
                                ? _fullNameController.text
                                : 'Your name',
                            style: GoogleFonts.sora(
                                fontSize: 20, fontWeight: FontWeight.w900)),
                        const SizedBox(height: 8),
                        Wrap(spacing: 8, runSpacing: 6, children: [
                          if (_jobController.text.isNotEmpty)
                            Chip(
                                backgroundColor: Colors.grey.shade50,
                                label: Text(_jobController.text,
                                    style: GoogleFonts.sora(
                                        fontSize: 12,
                                        color: Colors.grey.shade800))),
                          if (_companyController.text.isNotEmpty)
                            Chip(
                                backgroundColor: Colors.grey.shade50,
                                label: Text(_companyController.text,
                                    style: GoogleFonts.sora(
                                        fontSize: 12,
                                        color: Colors.grey.shade800))),
                          Chip(
                              backgroundColor: Colors.grey.shade50,
                              label: Row(
                                  mainAxisSize: MainAxisSize.min,
                                  children: [
                                    const Icon(Icons.location_on,
                                        size: 14, color: Colors.grey),
                                    const SizedBox(width: 6),
                                    Text(
                                        _countryController.text.isNotEmpty
                                            ? _countryController.text
                                            : 'Country',
                                        style: GoogleFonts.sora(fontSize: 12))
                                  ])),
                        ]),
                        const SizedBox(height: 8),
                        Text(
                            _aboutController.text.isNotEmpty
                                ? _aboutController.text
                                : 'A short friendly bio will appear here.',
                            style: GoogleFonts.sora(
                                fontSize: 13, color: Colors.grey.shade700),
                            maxLines: 3,
                            overflow: TextOverflow.ellipsis),
                      ])),
                ]),
              ),
              const SizedBox(height: 18),
              // Form card
              Form(
                key: _formKey,
                child: Container(
                  width: double.infinity,
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(12),
                    boxShadow: [
                      BoxShadow(
                          color: Colors.black.withOpacity(0.02),
                          blurRadius: 10,
                          offset: const Offset(0, 6))
                    ],
                    border: Border.all(color: Colors.grey.withOpacity(0.04)),
                  ),
                  child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('About Me',
                            style: GoogleFonts.sora(
                                fontSize: 14, fontWeight: FontWeight.w800)),
                        const SizedBox(height: 8),
                        _input(
                            controller: _aboutController,
                            label: 'Your Bio',
                            icon: Icons.edit,
                            enabled: true,
                            maxLines: 5,
                            hint:
                                'e.g. I build beautiful apps and love clean UI...'),
                        const SizedBox(height: 14),
                        LayoutBuilder(builder: (ctx, constraints) {
                          final twoCol = constraints.maxWidth >= 680;
                          if (twoCol) {
                            return Row(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Expanded(
                                      child: Column(children: [
                                    _input(
                                        controller: _fullNameController,
                                        label: 'Full Name',
                                        icon: Icons.person,
                                        enabled: false),
                                    const SizedBox(height: 12),
                                    _input(
                                        controller: _companyController,
                                        label: 'Company',
                                        icon: Icons.business),
                                    const SizedBox(height: 12),
                                    _input(
                                        controller: _countryController,
                                        label: 'Country',
                                        icon: Icons.flag),
                                  ])),
                                  const SizedBox(width: 12),
                                  Expanded(
                                      child: Column(children: [
                                    _input(
                                        controller: _emailController,
                                        label: 'Email',
                                        icon: Icons.email,
                                        enabled: false,
                                        keyboardType:
                                            TextInputType.emailAddress),
                                    const SizedBox(height: 12),
                                    _input(
                                        controller: _jobController,
                                        label: 'Job Title',
                                        icon: Icons.work),
                                    const SizedBox(height: 12),
                                    _input(
                                        controller: _phoneController,
                                        label: 'Phone',
                                        icon: Icons.phone,
                                        enabled: false,
                                        keyboardType: TextInputType.phone),
                                  ])),
                                ]);
                          } else {
                            return Column(children: [
                              _input(
                                  controller: _fullNameController,
                                  label: 'Full Name',
                                  icon: Icons.person,
                                  enabled: false),
                              const SizedBox(height: 12),
                              _input(
                                  controller: _emailController,
                                  label: 'Email',
                                  icon: Icons.email,
                                  enabled: false,
                                  keyboardType: TextInputType.emailAddress),
                              const SizedBox(height: 12),
                              _input(
                                  controller: _companyController,
                                  label: 'Company',
                                  icon: Icons.business),
                              const SizedBox(height: 12),
                              _input(
                                  controller: _jobController,
                                  label: 'Job Title',
                                  icon: Icons.work),
                              const SizedBox(height: 12),
                              _input(
                                  controller: _phoneController,
                                  label: 'Phone',
                                  icon: Icons.phone,
                                  enabled: false,
                                  keyboardType: TextInputType.phone),
                            ]);
                          }
                        }),
                        const SizedBox(height: 14),
                        _input(
                            controller: _addressController,
                            label: 'Address',
                            icon: Icons.location_on,
                            enabled: false),
                        const SizedBox(height: 18),
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _submitProfileUpdate,
                            style: ButtonStyle(
                              padding: MaterialStateProperty.all(
                                  const EdgeInsets.symmetric(vertical: 16)),
                              shape: MaterialStateProperty.all(
                                  RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(12))),
                              elevation: MaterialStateProperty.all(8),
                              shadowColor: MaterialStateProperty.all(
                                  Colors.black.withOpacity(0.18)),
                              backgroundColor:
                                  MaterialStateProperty.resolveWith((states) {
                                return Colors.transparent;
                              }),
                            ),
                            child: Ink(
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(colors: [
                                  Color(0xFF4A6DF5),
                                  Color(0xFF4154F1)
                                ]),
                                borderRadius: BorderRadius.circular(12),
                              ),
                              child: Container(
                                alignment: Alignment.center,
                                constraints:
                                    const BoxConstraints(minHeight: 48),
                                child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    mainAxisAlignment: MainAxisAlignment.center,
                                    children: [
                                      const Icon(Icons.save,
                                          color: Colors.white, size: 18),
                                      const SizedBox(width: 10),
                                      Text('Save Changes',
                                          style: GoogleFonts.sora(
                                              fontSize: 16,
                                              fontWeight: FontWeight.w800,
                                              color: Colors.white)),
                                    ]),
                              ),
                            ),
                          ),
                        ),
                      ]),
                ),
              ),
              const SizedBox(height: 12),
            ]),
          ),
        );
      },
    );
  }

  // ---------------- Password Tab ----------------
  Widget _passwordTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Form(
        key: _passwordFormKey,
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('🔒 Change Password',
              style: GoogleFonts.sora(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                  color: const Color(0xFF1A1D2E))),
          const SizedBox(height: 6),
          Text('Keep your account secure by choosing a strong password.',
              style: GoogleFonts.sora(
                  fontSize: 14, color: Colors.grey[600], height: 1.4)),
          const SizedBox(height: 28),
          Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                    color: Colors.black.withOpacity(0.05),
                    blurRadius: 12,
                    offset: const Offset(0, 4))
              ],
            ),
            child: Column(children: [
              _buildPasswordField(
                controller: _currentPasswordController,
                label: 'Current Password',
                icon: Icons.lock,
                isVisible: _currentVisible,
                toggleVisibility: () =>
                    setState(() => _currentVisible = !_currentVisible),
                validator: (value) {
                  if (value == null || value.isEmpty)
                    return 'Please enter your current password';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              _buildPasswordField(
                controller: _newPasswordController,
                label: 'New Password',
                icon: Icons.lock_outline,
                isVisible: _newVisible,
                toggleVisibility: () =>
                    setState(() => _newVisible = !_newVisible),
                validator: (value) {
                  if (value == null || value.isEmpty)
                    return 'Please enter a new password';
                  if (value.length < 6)
                    return 'Password must be at least 6 characters';
                  return null;
                },
              ),
              const SizedBox(height: 16),
              _buildPasswordField(
                controller: _confirmPasswordController,
                label: 'Confirm New Password',
                icon: Icons.lock_reset,
                isVisible: _confirmVisible,
                toggleVisibility: () =>
                    setState(() => _confirmVisible = !_confirmVisible),
                validator: (value) {
                  if (value == null || value.isEmpty)
                    return 'Please confirm your new password';
                  if (value != _newPasswordController.text)
                    return 'Passwords do not match';
                  return null;
                },
              ),
            ]),
          ),
          const SizedBox(height: 32),
          SizedBox(
            width: double.infinity,
            height: 54,
            child: ElevatedButton(
              onPressed: _submitPasswordChange,
              style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4154F1),
                  shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14)),
                  elevation: 4),
              child: Text('Change Password',
                  style: GoogleFonts.sora(
                      fontSize: 16,
                      fontWeight: FontWeight.w600,
                      color: Colors.white)),
            ),
          ),
        ]),
      ),
    );
  }

  Widget _buildPasswordField({
    required TextEditingController controller,
    required String label,
    required IconData icon,
    required bool isVisible,
    required VoidCallback toggleVisibility,
    required String? Function(String?) validator,
  }) {
    return TextFormField(
      controller: controller,
      obscureText: !isVisible,
      decoration: InputDecoration(
        labelText: label,
        prefixIcon: Icon(icon, color: const Color(0xFF4154F1)),
        suffixIcon: IconButton(
            icon: Icon(isVisible ? Icons.visibility : Icons.visibility_off,
                color: Colors.grey),
            onPressed: toggleVisibility),
        filled: true,
        fillColor: Colors.grey[50],
        contentPadding:
            const EdgeInsets.symmetric(vertical: 16, horizontal: 14),
        border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(12),
            borderSide: BorderSide.none),
      ),
      validator: validator,
    );
  }

  Widget _buildProfileCard(Map<String, dynamic> profile) {
    final avatarUrl = profile['profile_image'] as String?;
    final performance = (profile['performance'] as Map<String, dynamic>?) ?? {};
    final userEntry = (profile['user_entry'] as Map<String, dynamic>?) ?? {};
    final currentYear = profile['current_year'] ?? DateTime.now().year;

    final commissionRate = _toDouble(performance['commission_rate']);
    final closedDeals = _toInt(performance['closed_deals']);

    final hasTarget = userEntry['has_target'] ?? false;
    final diffPct = _toDouble(userEntry['diff_pct']);
    final userCategory = userEntry['category'] ?? '';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 4.0),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 600),
        curve: Curves.easeOutCubic,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(20),
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.white.withOpacity(0.95),
              Colors.white.withOpacity(0.92),
            ],
          ),
          boxShadow: [
            BoxShadow(
                color: Colors.black.withOpacity(0.06),
                blurRadius: 24,
                offset: const Offset(0, 12)),
            BoxShadow(
                color: const Color(0xFF4154F1).withOpacity(0.04),
                blurRadius: 40,
                offset: const Offset(0, 8)),
          ],
          border: Border.all(color: Colors.white.withOpacity(0.6)),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(20),
          child: Material(
            color: Colors.transparent,
            child: InkWell(
              onTap: () {
                if (_tabController.index != 0) _tabController.animateTo(0);
              },
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(children: [
                  Row(children: [
                    Hero(
                      tag: 'profile-image',
                      child: Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          gradient: LinearGradient(
                              colors: [
                                const Color(0xFF4154F1).withOpacity(0.12),
                                Colors.transparent
                              ],
                              begin: Alignment.topLeft,
                              end: Alignment.bottomRight),
                          boxShadow: [
                            BoxShadow(
                                color: Colors.black.withOpacity(0.08),
                                blurRadius: 12,
                                offset: const Offset(0, 6))
                          ],
                        ),
                        child: ClipOval(
                          child: avatarUrl != null && avatarUrl.isNotEmpty
                              ? FadeInImage.assetNetwork(
                                  placeholder: 'assets/avater.webp',
                                  image: avatarUrl,
                                  fit: BoxFit.cover)
                              : Image.asset('assets/avater.webp',
                                  fit: BoxFit.cover),
                        ),
                      ),
                    ),
                    const SizedBox(width: 16),
                    Expanded(
                        child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                          Text(profile['full_name'] ?? 'Unnamed Marketer',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.sora(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w700,
                                  color: const Color(0xFF111827))),
                          const SizedBox(height: 6),
                          Text(profile['job'] ?? profile['company'] ?? '',
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: GoogleFonts.sora(
                                  fontSize: 13, color: Colors.grey[700])),
                          const SizedBox(height: 8),
                        ])),
                  ]),
                  const SizedBox(height: 18),
                  Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                        vertical: 12, horizontal: 12),
                    decoration: BoxDecoration(
                        color: const Color(0x0C2575FC),
                        borderRadius: BorderRadius.circular(12)),
                    child: Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          // Commission Rate
                          Column(children: [
                            Text('${commissionRate.toStringAsFixed(1)}%',
                                style: GoogleFonts.sora(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w800,
                                    color: const Color(0xFF2575FC))),
                            const SizedBox(height: 6),
                            Text('Commission',
                                style: GoogleFonts.sora(
                                    fontSize: 12, color: Colors.grey[700]))
                          ]),
                          // Year target
                          Column(children: [
                            if (hasTarget)
                              Text(
                                  '+${diffPct.toStringAsFixed(0)}% $userCategory',
                                  style: GoogleFonts.sora(
                                      fontSize: 14,
                                      fontWeight: FontWeight.w700,
                                      color: Colors.black87))
                            else
                              Text('Target not set',
                                  style: GoogleFonts.sora(
                                      fontSize: 12,
                                      fontStyle: FontStyle.italic,
                                      color: Colors.grey[700])),
                            const SizedBox(height: 6),
                            Text('$currentYear Target',
                                style: GoogleFonts.sora(
                                    fontSize: 12, color: Colors.grey[700]))
                          ]),
                          // Closed deals
                          Column(children: [
                            Text('$closedDeals',
                                style: GoogleFonts.sora(
                                    fontSize: 18,
                                    fontWeight: FontWeight.w800,
                                    color: const Color(0xFF111827))),
                            const SizedBox(height: 6),
                            Text('Closed Deals (All Companies)',
                                style: GoogleFonts.sora(
                                    fontSize: 12, color: Colors.grey[700]))
                          ]),
                        ]),
                  ),
                  const SizedBox(height: 14),
                  Row(mainAxisAlignment: MainAxisAlignment.start, children: [
                    Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                            gradient: const LinearGradient(
                                colors: [Color(0xFFFFD700), Color(0xFFFFA500)]),
                            borderRadius: BorderRadius.circular(20)),
                        child: Text('Gold',
                            style: GoogleFonts.sora(
                                color: Colors.black,
                                fontWeight: FontWeight.w600))),
                    const SizedBox(width: 8),
                    Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                            gradient: const LinearGradient(
                                colors: [Color(0xFFC0C0C0), Color(0xFFA9A9A9)]),
                            borderRadius: BorderRadius.circular(20)),
                        child: Text('Elite Marketer',
                            style: GoogleFonts.sora(
                                color: Colors.black,
                                fontWeight: FontWeight.w600))),
                    const SizedBox(width: 8),
                    Container(
                        padding: const EdgeInsets.symmetric(
                            horizontal: 10, vertical: 6),
                        decoration: BoxDecoration(
                            gradient: const LinearGradient(
                                colors: [Color(0xFFCD7F32), Color(0xFF8B4513)]),
                            borderRadius: BorderRadius.circular(20)),
                        child: Text('Consistent',
                            style: GoogleFonts.sora(
                                color: Colors.white,
                                fontWeight: FontWeight.w600))),
                  ]),
                ]),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildContactInfoCard(Map<String, dynamic> profile) {
    final email = profile['email'] ?? 'Not specified';
    final phone = profile['phone'] ?? 'Not specified';
    final address = profile['address'] ?? 'Not specified';
    final company = profile['company'] ?? 'Not specified';

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 4.0),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 450),
        curve: Curves.easeOut,
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          color: Colors.white,
          boxShadow: [
            BoxShadow(
                color: Colors.black.withOpacity(0.04),
                blurRadius: 18,
                offset: const Offset(0, 12))
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 14.0, vertical: 14.0),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('Contact Information',
                  style: GoogleFonts.sora(
                      fontSize: 18, fontWeight: FontWeight.bold)),
              const Spacer(),
              IconButton(
                  tooltip: 'Message',
                  onPressed: () {},
                  icon: const Icon(Icons.message_outlined,
                      color: Color(0xFF4154F1))),
              IconButton(
                  tooltip: 'Call',
                  onPressed: () {},
                  icon: const Icon(Icons.call_outlined,
                      color: Color(0xFF10B981))),
            ]),
            const SizedBox(height: 12),
            _buildContactItem(
                icon: Icons.email_outlined,
                label: 'Email',
                value: email,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: email));
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: Text('Email copied to clipboard')));
                }),
            _buildContactItem(
                icon: Icons.phone_outlined,
                label: 'Phone',
                value: phone,
                onTap: () {
                  Clipboard.setData(ClipboardData(text: phone));
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: Text('Phone copied to clipboard')));
                }),
            _buildContactItem(
                icon: Icons.location_on_outlined,
                label: 'Address',
                value: address),
            _buildContactItem(
                icon: Icons.business_outlined,
                label: 'Company',
                value: company),
          ]),
        ),
      ),
    );
  }

  Widget _buildContactItem(
      {required IconData icon,
      required String label,
      required String value,
      GestureTapCallback? onTap}) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Row(children: [
          Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                  color: const Color(0xFF4154F1).withOpacity(0.06),
                  borderRadius: BorderRadius.circular(10)),
              child: Icon(icon, size: 18, color: const Color(0xFF4154F1))),
          const SizedBox(width: 12),
          Expanded(
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                Text(label,
                    style: GoogleFonts.sora(
                        fontSize: 12, color: Colors.grey[600])),
                const SizedBox(height: 2),
                Text(value,
                    style: GoogleFonts.sora(
                        fontSize: 14, fontWeight: FontWeight.w600))
              ])),
          if (onTap != null)
            Padding(
                padding: const EdgeInsets.only(left: 8.0),
                child: Icon(Icons.copy, size: 16, color: Colors.grey[400])),
        ]),
      ),
    );
  }

  Widget _buildProfileDetails(Map<String, dynamic> profile) {
    final about =
        profile['about'] as String? ?? 'Share something about yourself...';
    final rawDate = profile['date_registered'];
    String dateRegistered = 'Not specified';
    if (rawDate != null) {
      try {
        final dt = DateTime.parse(rawDate.toString());
        dateRegistered = DateFormat.yMMMMd().format(dt);
      } catch (_) {
        dateRegistered = rawDate.toString();
      }
    }

    final country = profile['country']?.toString() ?? '-';
    final fullName = profile['full_name']?.toString() ?? '-';
    final job = profile['job']?.toString() ?? '-';
    final company = profile['company']?.toString() ?? '-';
    final address = profile['address']?.toString() ?? '-';
    final phone = profile['phone']?.toString() ?? '-';
    final email = profile['email']?.toString() ?? '-';

    final bool isLong = about.length > 140;
    final preview = isLong ? '${about.substring(0, 140)}…' : about;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0, horizontal: 4.0),
      child: Container(
        decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            color: Colors.white,
            boxShadow: [
              BoxShadow(
                  color: Colors.black.withOpacity(0.03),
                  blurRadius: 18,
                  offset: const Offset(0, 12))
            ]),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child:
              Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Text('About You',
                  style: GoogleFonts.sora(
                      fontSize: 18, fontWeight: FontWeight.bold)),
              const Spacer(),
              IconButton(
                  onPressed: () => _tabController.animateTo(3),
                  icon: const Icon(Icons.edit_outlined,
                      color: Color(0xFF4154F1))),
            ]),
            const SizedBox(height: 8),
            AnimatedCrossFade(
                firstChild: Text(preview,
                    style: GoogleFonts.sora(
                        fontStyle: FontStyle.italic, color: Colors.grey[700])),
                secondChild: Text(about,
                    style: GoogleFonts.sora(
                        fontStyle: FontStyle.italic, color: Colors.grey[800])),
                crossFadeState: isLong
                    ? CrossFadeState.showFirst
                    : CrossFadeState.showSecond,
                duration: const Duration(milliseconds: 450)),
            if (isLong)
              Align(
                  alignment: Alignment.centerLeft,
                  child: TextButton(
                      onPressed: () => showDialog(
                          context: context,
                          builder: (ctx) => AlertDialog(
                                  title: Text('About You',
                                      style: GoogleFonts.sora()),
                                  content:
                                      Text(about, style: GoogleFonts.sora()),
                                  actions: [
                                    TextButton(
                                        onPressed: () =>
                                            Navigator.of(ctx).pop(),
                                        child: Text('Close',
                                            style: GoogleFonts.sora()))
                                  ])),
                      child: Text('Read more',
                          style: GoogleFonts.sora(
                              color: const Color(0xFF4154F1))))),
            const SizedBox(height: 12),
            Text('Profile Details',
                style: GoogleFonts.sora(
                    fontSize: 18, fontWeight: FontWeight.bold)),
            const SizedBox(height: 12),
            Wrap(spacing: 12, runSpacing: 12, children: [
              _buildInfoItem(label: 'Full Name', value: fullName),
              _buildInfoItem(label: 'Company', value: company),
              _buildInfoItem(label: 'Job', value: job),
              _buildInfoItem(label: 'Country', value: country),
              _buildInfoItem(label: 'Address', value: address),
              _buildInfoItem(label: 'Phone', value: phone),
              _buildInfoItem(label: 'Email', value: email),
              _buildInfoItem(label: 'Date Registered', value: dateRegistered),
            ]),
          ]),
        ),
      ),
    );
  }

  Widget _buildInfoItem({required String label, required String value}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      constraints: const BoxConstraints(minWidth: 160, maxWidth: 320),
      decoration: BoxDecoration(
          color: const Color(0xFFF8FAFF),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: Colors.grey.withOpacity(0.06))),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label,
            style: GoogleFonts.sora(fontSize: 12, color: Colors.grey[600])),
        const SizedBox(height: 6),
        Text(value,
            style: GoogleFonts.sora(fontSize: 14, fontWeight: FontWeight.w700)),
      ]),
    );
  }

  Widget _buildShimmerLoader() {
    return ListView(padding: const EdgeInsets.all(16), children: [
      Shimmer.fromColors(
          baseColor: Colors.grey[300]!,
          highlightColor: Colors.grey[100]!,
          child: Container(
              height: 140,
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16)))),
      const SizedBox(height: 14),
      Shimmer.fromColors(
          baseColor: Colors.grey[300]!,
          highlightColor: Colors.grey[100]!,
          child: Row(children: [
            Expanded(
                child: Container(
                    height: 90,
                    decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12)))),
            const SizedBox(width: 12),
            Expanded(
                child: Container(
                    height: 90,
                    decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12))))
          ])),
      const SizedBox(height: 14),
      Shimmer.fromColors(
          baseColor: Colors.grey[300]!,
          highlightColor: Colors.grey[100]!,
          child: Container(
              height: 220,
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16)))),
    ]);
  }
}

class _SliverAppBarDelegate extends SliverPersistentHeaderDelegate {
  final TabBar _tabBar;

  _SliverAppBarDelegate(this._tabBar);

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(color: Colors.white, child: _tabBar);
  }

  @override
  double get maxExtent => _tabBar.preferredSize.height;

  @override
  double get minExtent => _tabBar.preferredSize.height;

  @override
  bool shouldRebuild(_SliverAppBarDelegate oldDelegate) => false;
}
