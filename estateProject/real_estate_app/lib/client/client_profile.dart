import 'dart:io';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:real_estate_app/client/client_plot_details.dart';
import 'package:shimmer/shimmer.dart';
import 'package:real_estate_app/core/api_service.dart';
import 'package:real_estate_app/shared/app_layout.dart';
import 'package:real_estate_app/client/client_bottom_nav.dart';
import 'package:real_estate_app/shared/app_side.dart';

class ClientProfile extends StatefulWidget {
  final String token;

  const ClientProfile({Key? key, required this.token}) : super(key: key);

  @override
  _ClientProfileState createState() => _ClientProfileState();
}

class _ClientProfileState extends State<ClientProfile>
    with TickerProviderStateMixin {
  // ===== CONTROLLERS =====
  late TabController _tabController;
  late AnimationController _glowController;

  // ===== IMAGE & FILE PICKERS =====
  final ImagePicker _picker = ImagePicker();
  File? _imageFile;

  // ===== FORM KEYS =====
  final GlobalKey<FormState> _formKey = GlobalKey<FormState>();
  final GlobalKey<FormState> _passwordFormKey = GlobalKey<FormState>();

  // ===== TEXT EDITING CONTROLLERS - PROFILE FIELDS =====
  final TextEditingController _titleController = TextEditingController();
  final TextEditingController _fullNameController = TextEditingController();
  final TextEditingController _dobController = TextEditingController();
  final TextEditingController _aboutController = TextEditingController();
  final TextEditingController _companyController = TextEditingController();
  final TextEditingController _jobController = TextEditingController();
  final TextEditingController _countryController = TextEditingController();
  final TextEditingController _addressController = TextEditingController();
  final TextEditingController _phoneController = TextEditingController();
  final TextEditingController _emailController = TextEditingController();

  // ===== TEXT EDITING CONTROLLERS - PASSWORD FIELDS =====
  final TextEditingController _currentPasswordController =
      TextEditingController();
  final TextEditingController _newPasswordController = TextEditingController();
  final TextEditingController _confirmPasswordController =
      TextEditingController();

  // ===== STATE & UI FLAGS =====
  bool _isEditing = false;
  bool _currentVisible = false;
  bool _newVisible = false;
  bool _confirmVisible = false;

  // ===== DATA STATES =====
  String? _headerImageUrl;
  late Future<Map<String, dynamic>> _profileFuture;

  double _toDouble(dynamic v) {
    if (v == null) return 0.0;
    if (v is double) return v;
    if (v is int) return v.toDouble();
    if (v is String) {
      final cleaned = v.replaceAll(RegExp(r'[^0-9\.-]'), '');
      return double.tryParse(cleaned) ?? 0.0;
    }
    return 0.0;
  }

  int _toInt(dynamic v) {
    if (v == null) return 0;
    if (v is int) return v;
    if (v is double) return v.toInt();
    if (v is String)
      return int.tryParse(v.replaceAll(RegExp(r'[^0-9-]'), '')) ?? 0;
    return 0;
  }

  String formatCurrency(num value,
      {int decimalDigits = 2, bool forceSignForPositive = false}) {
    try {
      final f = NumberFormat.currency(
          locale: 'en_NG', symbol: '₦', decimalDigits: decimalDigits);
      final s = f.format(value);
      if (forceSignForPositive && value > 0) return '+$s';
      return s;
    } catch (e) {
      final s = '₦' + value.toStringAsFixed(decimalDigits);
      if (forceSignForPositive && value > 0) return '+$s';
      return s;
    }
  }

  @override
  void initState() {
    super.initState();

    _tabController = TabController(length: 3, vsync: this);

    // Glow controller
    _glowController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);

    _loadData();
  }

  void _loadData() {
    // Load overview profile data (avatar, stats, contact, portfolio summary, best estate)
    _profileFuture =
        ApiService().getClientProfileOverview(token: widget.token).then((data) {
      final maybeHeader = data['profile_image'];
      if (maybeHeader is String && maybeHeader.isNotEmpty) {
        setState(() {
          _headerImageUrl = maybeHeader;
        });
      }
      return data;
    });
  }

  @override
  void dispose() {
    _glowController.dispose();
    _tabController.dispose();

    _titleController.dispose();
    _fullNameController.dispose();
    _dobController.dispose();
    _aboutController.dispose();
    _companyController.dispose();
    _jobController.dispose();
    _countryController.dispose();
    _addressController.dispose();
    _phoneController.dispose();
    _emailController.dispose();
    _currentPasswordController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _pickImage() async {
    final pickedFile = await _picker.pickImage(source: ImageSource.gallery);
    if (pickedFile != null) {
      setState(() {
        _imageFile = File(pickedFile.path);
      });
    }
  }

  Future<void> _updateProfile() async {
    if (_formKey.currentState!.validate()) {
      try {
        final updatedProfile = await ApiService().updateClientProfileByToken(
          token: widget.token,
          title: _titleController.text.trim().isNotEmpty
              ? _titleController.text
              : null,
          fullName: _fullNameController.text,
          about: _aboutController.text.trim().isNotEmpty
              ? _aboutController.text
              : null,
          dateOfBirth: _dobController.text.trim().isNotEmpty
              ? _dobController.text
              : null,
          company: _companyController.text.trim().isNotEmpty
              ? _companyController.text
              : null,
          job: _jobController.text.trim().isNotEmpty
              ? _jobController.text
              : null,
          country: _countryController.text.trim().isNotEmpty
              ? _countryController.text
              : null,
          address: _addressController.text.trim().isNotEmpty
              ? _addressController.text
              : null,
          phone: _phoneController.text.trim().isNotEmpty
              ? _phoneController.text
              : null,
          profileImage: _imageFile,
        );

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Profile updated successfully!',
                style: GoogleFonts.sora(color: Colors.white)),
            backgroundColor: Colors.green,
          ),
        );

        setState(() {
          _profileFuture = Future.value(updatedProfile);
          _isEditing = false;
          _imageFile = null;
        });
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error updating profile: $e',
                style: GoogleFonts.sora(color: Colors.white)),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  Future<void> _changePassword() async {
    if (_passwordFormKey.currentState!.validate()) {
      if (_newPasswordController.text != _confirmPasswordController.text) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Passwords do not match',
                style: GoogleFonts.sora(color: Colors.white)),
            backgroundColor: Colors.red,
          ),
        );
        return;
      }

      try {
        await ApiService().changePasswordByToken(
          token: widget.token,
          currentPassword: _currentPasswordController.text,
          newPassword: _newPasswordController.text,
          confirmPassword: _confirmPasswordController.text,
        );

        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Password changed successfully!',
                style: GoogleFonts.sora(color: Colors.white)),
            backgroundColor: Colors.green,
          ),
        );

        // Clear password fields
        _currentPasswordController.clear();
        _newPasswordController.clear();
        _confirmPasswordController.clear();
      } catch (e) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Error changing password: $e',
                style: GoogleFonts.sora(color: Colors.white)),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppLayout(
      pageTitle: 'Profile',
      token: widget.token,
      side: AppSide.client,
      child: AnnotatedRegion<SystemUiOverlayStyle>(
        value: SystemUiOverlayStyle.light.copyWith(
          statusBarColor: Colors.transparent,
          statusBarIconBrightness: Brightness.light,
          statusBarBrightness: Brightness.light,
        ),
        child: Scaffold(
          extendBodyBehindAppBar: true,
          backgroundColor: Colors.transparent,
          bottomNavigationBar: ClientBottomNav(
            currentIndex: 1,
            token: widget.token,
            chatBadge: 1,
          ),
          body: NestedScrollView(
            floatHeaderSlivers: true,
            headerSliverBuilder: (context, innerBoxIsScrolled) {
              final double topPadding = MediaQuery.of(context).padding.top;
              final double expandedHeight = 280.0 + topPadding;

              return [
                SliverAppBar(
                  backgroundColor: Colors.transparent,
                  surfaceTintColor: Colors.transparent, // ✅ prevent white tint
                  shadowColor: Colors.transparent, // ✅ no shadow glow
                  elevation: 0,
                  pinned: true,
                  stretch: true,
                  expandedHeight: expandedHeight,
                  automaticallyImplyLeading: false,
                  centerTitle: false,
                  systemOverlayStyle: SystemUiOverlayStyle.light.copyWith(
                    statusBarColor: Colors.transparent,
                  ),
                  toolbarHeight: kToolbarHeight + topPadding,
                  collapsedHeight: kToolbarHeight + topPadding,
                  flexibleSpace: LayoutBuilder(
                    builder: (context, constraints) {
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
                          (smallTitleLeftExpanded - smallTitleLeftCollapsed) *
                              t;

                      final Widget backgroundImageWidget =
                          (_headerImageUrl != null &&
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
                                    fit: BoxFit.cover,
                                  ),
                                )
                              : Image.asset(
                                  'assets/avater.webp',
                                  fit: BoxFit.cover,
                                );

                      final double glowScale =
                          0.85 + (_glowController.value) * (1.35 - 0.85);
                      final double glowFactor = glowScale * (0.7 + 0.3 * t);

                      return Stack(
                        fit: StackFit.expand,
                        children: [
                          // ✅ Background image fills without shifting (no white gap)
                          Positioned.fill(child: backgroundImageWidget),

                          // ✅ Gradient overlay (keeps readability)
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

                          // Large expanded title
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

                          // Small collapsed title
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

                          // Avatar (shrinks / slides / glows)
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
                    },
                  ),
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
                        Tab(text: 'Overview'),
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
                _buildOverviewTab(),
                _buildEditProfileTab(),
                _buildPasswordTab(),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildOverviewTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _profileFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return _buildShimmerLoader();
        }
        if (snapshot.hasError) {
          return Center(child: Text('Error: ${snapshot.error}'));
        }
        final profile = snapshot.data!;

        return CustomScrollView(
          slivers: [
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: _buildProfileCard(profile),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: _buildProfileDetails(profile),
              ),
            ),
            SliverToBoxAdapter(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    const SizedBox(height: 16),
                    _buildContactInfoCard(profile),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  // ===== HELPER METHODS =====

  Color _getStatusColor(String? status) {
    switch (status?.toLowerCase()) {
      case 'paid complete':
      case 'fully paid':
        return Colors.green;
      case 'part payment':
        return Colors.orange;
      case 'overdue':
        return Colors.red;
      default:
        return Colors.grey;
    }
  }

  // ===== CANONICAL METHODS ONLY: _buildEditProfileTab and below

  Widget _buildEditProfileTab() {
    return FutureBuilder<Map<String, dynamic>>(
      future: _profileFuture,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting)
          return _buildShimmerLoader();
        if (snapshot.hasError)
          return Center(child: Text('Error: ${snapshot.error}'));

        final profile = snapshot.data!;

        // Initialize controllers once (keeps user edits across rebuilds)
        if (!_isEditing) {
          _titleController.text = (profile['title'] ?? '').toString();
          _fullNameController.text = (profile['full_name'] ?? '').toString();
          _dobController.text = (profile['date_of_birth'] ?? '').toString();
          _aboutController.text = (profile['about'] ?? '').toString();
          _companyController.text = (profile['company'] ?? '').toString();
          _jobController.text = (profile['job'] ?? '').toString();
          _countryController.text = (profile['country'] ?? '').toString();
          _addressController.text = (profile['address'] ?? '').toString();
          _phoneController.text = (profile['phone'] ?? '').toString();
          _emailController.text = (profile['email'] ?? '').toString();
          _isEditing = true;
        }

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
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
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
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.center,
                    children: [
                      // Avatar
                      Stack(
                        alignment: Alignment.bottomRight,
                        children: [
                          CircleAvatar(
                            radius: 48,
                            backgroundColor: Colors.grey.shade100,
                            backgroundImage: _imageFile != null
                                ? FileImage(_imageFile!)
                                : (profile['profile_image'] != null
                                    ? NetworkImage(
                                        profile['profile_image'] as String)
                                    : const AssetImage(
                                        'assets/avater.webp')) as ImageProvider,
                          ),
                          Container(
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(colors: [
                                Color(0xFF4154F1),
                                Color(0xFF6C7BFF)
                              ]),
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
                        ],
                      ),

                      const SizedBox(width: 16),

                      // Info area (uses Expanded to avoid overflow)
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              _fullNameController.text.isNotEmpty
                                  ? _fullNameController.text
                                  : 'Your name',
                              style: GoogleFonts.sora(
                                  fontSize: 20, fontWeight: FontWeight.w900),
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 8),

                            // Chips area
                            LayoutBuilder(builder: (ctx, c) {
                              return ConstrainedBox(
                                constraints:
                                    BoxConstraints(maxWidth: c.maxWidth),
                                child: Wrap(
                                  spacing: 8,
                                  runSpacing: 6,
                                  children: [
                                    if (_jobController.text.isNotEmpty)
                                      Chip(
                                        backgroundColor: Colors.grey.shade50,
                                        label: Text(_jobController.text,
                                            style: GoogleFonts.sora(
                                                fontSize: 12,
                                                color: Colors.grey.shade800)),
                                      ),
                                    if (_companyController.text.isNotEmpty)
                                      Chip(
                                        backgroundColor: Colors.grey.shade50,
                                        label: Text(_companyController.text,
                                            style: GoogleFonts.sora(
                                                fontSize: 12,
                                                color: Colors.grey.shade800)),
                                      ),
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
                                              style: GoogleFonts.sora(
                                                  fontSize: 12)),
                                        ],
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            }),

                            const SizedBox(height: 8),
                            Text(
                              _aboutController.text.isNotEmpty
                                  ? _aboutController.text
                                  : 'A short friendly bio will appear here.',
                              style: GoogleFonts.sora(
                                  fontSize: 13, color: Colors.grey.shade700),
                              maxLines: 3,
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 18),

                // Form card
                Form(
                  key: _formKey,
                  child: Container(
                    width: double.infinity,
                    padding: const EdgeInsets.symmetric(
                        horizontal: 14, vertical: 14),
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
                        // About Me
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
                          hint: 'e.g. Who you are...',
                        ),
                        const SizedBox(height: 14),

                        // Responsive two-column section (fields)
                        LayoutBuilder(builder: (ctx, constraints) {
                          final twoCol = constraints.maxWidth >= 680;
                          if (twoCol) {
                            return Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                // Left column
                                Expanded(
                                  child: Column(children: [
                                    _input(
                                      controller: _fullNameController,
                                      label: 'Full Name',
                                      icon: Icons.person,
                                      enabled: false,
                                    ),
                                    const SizedBox(height: 12),
                                    _input(
                                        controller: _companyController,
                                        label: 'Company',
                                        icon: Icons.business),
                                    const SizedBox(height: 12),
                                    // Country field (editable here)
                                    _input(
                                        controller: _countryController,
                                        label: 'Country',
                                        icon: Icons.flag,
                                        enabled: true,
                                        keyboardType: TextInputType.text),
                                  ]),
                                ),
                                const SizedBox(width: 12),

                                // Right column
                                Expanded(
                                  child: Column(children: [
                                    _input(
                                      controller: _emailController,
                                      label: 'Email',
                                      icon: Icons.email,
                                      enabled: false,
                                      keyboardType: TextInputType.emailAddress,
                                    ),
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
                                      keyboardType: TextInputType.phone,
                                    ),
                                  ]),
                                ),
                              ],
                            );
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
                                  label: 'Your Company',
                                  icon: Icons.business),
                              const SizedBox(height: 12),
                              _input(
                                  controller: _jobController,
                                  label: 'Your Job Title',
                                  icon: Icons.work),
                              const SizedBox(height: 12),
                              // Country input for small screens (editable)
                              _input(
                                  controller: _countryController,
                                  label: 'Country',
                                  icon: Icons.flag,
                                  enabled: true,
                                  keyboardType: TextInputType.text),
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
                            enabled: false,
                            icon: Icons.location_on),

                        const SizedBox(height: 18),

                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton(
                            onPressed: _updateProfile,
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
                                  ],
                                ),
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 12),
              ],
            ),
          ),
        );
      },
    );
  }

  Widget _buildPasswordTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(20),
      child: Form(
        key: _passwordFormKey,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '🔒 Change Password',
              style: GoogleFonts.sora(
                fontSize: 22,
                fontWeight: FontWeight.w700,
                color: const Color(0xFF1A1D2E),
              ),
            ),
            const SizedBox(height: 6),
            Text(
              'Keep your account secure by choosing a strong password.',
              style: GoogleFonts.sora(
                fontSize: 14,
                color: Colors.grey[600],
                height: 1.4,
              ),
            ),
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
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: Column(
                children: [
                  _buildPasswordField(
                    controller: _currentPasswordController,
                    label: 'Current Password',
                    icon: Icons.lock,
                    isVisible: _currentVisible,
                    toggleVisibility: () {
                      setState(() => _currentVisible = !_currentVisible);
                    },
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter your current password';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  _buildPasswordField(
                    controller: _newPasswordController,
                    label: 'New Password',
                    icon: Icons.lock_outline,
                    isVisible: _newVisible,
                    toggleVisibility: () {
                      setState(() => _newVisible = !_newVisible);
                    },
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please enter a new password';
                      }
                      if (value.length < 6) {
                        return 'Password must be at least 6 characters';
                      }
                      return null;
                    },
                  ),
                  const SizedBox(height: 16),
                  _buildPasswordField(
                    controller: _confirmPasswordController,
                    label: 'Confirm New Password',
                    icon: Icons.lock_reset,
                    isVisible: _confirmVisible,
                    toggleVisibility: () {
                      setState(() => _confirmVisible = !_confirmVisible);
                    },
                    validator: (value) {
                      if (value == null || value.isEmpty) {
                        return 'Please confirm your new password';
                      }
                      if (value != _newPasswordController.text) {
                        return 'Passwords do not match';
                      }
                      return null;
                    },
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),
            SizedBox(
              width: double.infinity,
              height: 54,
              child: ElevatedButton(
                onPressed: _changePassword,
                style: ElevatedButton.styleFrom(
                  backgroundColor: const Color(0xFF4154F1),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                  ),
                  elevation: 4,
                ),
                child: Text(
                  'Change Password',
                  style: GoogleFonts.sora(
                    fontSize: 16,
                    fontWeight: FontWeight.w600,
                    color: Colors.white,
                  ),
                ),
              ),
            ),
          ],
        ),
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
          icon: Icon(
            isVisible ? Icons.visibility : Icons.visibility_off,
            color: Colors.grey,
          ),
          onPressed: toggleVisibility,
        ),
        filled: true,
        fillColor: Colors.grey[50],
        contentPadding:
            const EdgeInsets.symmetric(vertical: 16, horizontal: 14),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: BorderSide.none,
        ),
      ),
      validator: validator,
    );
  }

  // END OF PASSWORD TAB SECTION

  Widget _buildProfileCard(Map<String, dynamic> profile) {
    final propertiesCount = _toInt(profile['properties_count']);
    final totalValue = _toDouble(profile['total_value']);
    final avatarUrl = profile['profile_image'] as String?;

    final dynamic assignedRaw = profile['assigned_marketer'];
    Map<String, dynamic>? assigned;

    if (assignedRaw == null) {
      assigned = null;
    } else if (assignedRaw is Map<String, dynamic>) {
      assigned = Map<String, dynamic>.from(assignedRaw);
    } else if (assignedRaw is Map) {
      assigned = Map<String, dynamic>.from(
          assignedRaw.map((k, v) => MapEntry(k.toString(), v)));
    } else {
      assigned = null;
    }

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
              Colors.white.withOpacity(0.85),
              Colors.white.withOpacity(0.72),
            ],
            stops: const [0.0, 0.9],
          ),
          boxShadow: [
            BoxShadow(
              color: Colors.black.withOpacity(0.06),
              blurRadius: 24,
              offset: const Offset(0, 12),
            ),
            BoxShadow(
              color: const Color(0xFF4154F1).withOpacity(0.06),
              blurRadius: 40,
              offset: const Offset(0, 8),
            ),
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
                // Use LayoutBuilder here to make stats area responsive
                child: LayoutBuilder(builder: (context, constraints) {
                  // compute a responsive max width for the mini chart
                  final double maxChartWidth =
                      (constraints.maxWidth * 0.28).clamp(60.0, 110.0);

                  return Column(
                    children: [
                      // header row: avatar + name + marketer badge (animated)
                      Row(
                        children: [
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
                                    Colors.transparent,
                                  ],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                boxShadow: [
                                  BoxShadow(
                                    color: Colors.black.withOpacity(0.08),
                                    blurRadius: 12,
                                    offset: const Offset(0, 6),
                                  ),
                                ],
                              ),
                              child: ClipOval(
                                child: avatarUrl != null && avatarUrl.isNotEmpty
                                    ? FadeInImage.assetNetwork(
                                        placeholder: 'assets/avater.webp',
                                        image: avatarUrl,
                                        fit: BoxFit.cover,
                                      )
                                    : Image.asset(
                                        'assets/avater.webp',
                                        fit: BoxFit.cover,
                                      ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  profile['full_name'] ?? 'Valued Client',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: GoogleFonts.sora(
                                    fontSize: 20,
                                    fontWeight: FontWeight.w700,
                                    color: const Color(0xFF111827),
                                  ),
                                ),
                                const SizedBox(height: 6),
                                Text(
                                  profile['company'] ?? profile['job'] ?? '',
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: GoogleFonts.sora(
                                    fontSize: 13,
                                    color: Colors.grey[700],
                                  ),
                                ),
                                const SizedBox(height: 8),

                                // <-- changed Row to Wrap so badges don't force overflow -->
                                Wrap(
                                  spacing: 8,
                                  runSpacing: 6,
                                  crossAxisAlignment: WrapCrossAlignment.center,
                                  children: [
                                    _buildRankBadge(profile['rank_tag'] ??
                                        'First-Time Investor'),
                                    AnimatedSwitcher(
                                      duration:
                                          const Duration(milliseconds: 450),
                                      switchInCurve: Curves.easeOutBack,
                                      child: assigned != null
                                          ? _buildMarketerBadge(assigned)
                                          : SizedBox(
                                              key:
                                                  const ValueKey('no_marketer'),
                                              child: Text(
                                                'No marketer assigned',
                                                style: GoogleFonts.sora(
                                                    fontSize: 12,
                                                    color: Colors.grey),
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

                      const SizedBox(height: 18),

                      // Animated stats row with a mini chart
                      Row(
                        children: [
                          Flexible(
                            flex: 1,
                            child: TweenAnimationBuilder<double>(
                              tween: Tween(
                                  begin: 0, end: propertiesCount.toDouble()),
                              duration: const Duration(milliseconds: 900),
                              builder: (context, value, child) {
                                return Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      value.toInt().toString(),
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: GoogleFonts.sora(
                                        fontSize: 20,
                                        fontWeight: FontWeight.bold,
                                        color: const Color(0xFF4154F1),
                                      ),
                                    ),
                                    const SizedBox(height: 4),
                                    Text(
                                      'Properties',
                                      maxLines: 1,
                                      overflow: TextOverflow.ellipsis,
                                      style: GoogleFonts.sora(
                                          fontSize: 12, color: Colors.grey),
                                    ),
                                  ],
                                );
                              },
                            ),
                          ),

                          // thin divider (keeps fixed width 1)
                          Padding(
                            padding:
                                const EdgeInsets.symmetric(horizontal: 8.0),
                            child: Container(
                                height: 36, width: 1, color: Colors.grey[200]),
                          ),

                          Flexible(
                            flex: 1,
                            child: TweenAnimationBuilder<double>(
                              tween: Tween(begin: 0, end: totalValue),
                              duration: const Duration(milliseconds: 1100),
                              builder: (
                                context,
                                value,
                                child,
                              ) {
                                final display = value >= 1000
                                    ? formatCurrency(value, decimalDigits: 0)
                                    : formatCurrency(value, decimalDigits: 2);
                                return Padding(
                                  padding: const EdgeInsets.only(
                                      left: 4.0, right: 4.0),
                                  child: Column(
                                    crossAxisAlignment:
                                        CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        display,
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: GoogleFonts.roboto(
                                          fontSize: 16,
                                          fontWeight: FontWeight.w700,
                                          color: const Color(0xFF10B981),
                                        ),
                                      ),
                                      const SizedBox(height: 4),
                                      Text('Total Investment',
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: GoogleFonts.roboto(
                                              fontSize: 12,
                                              color: Colors.grey)),
                                    ],
                                  ),
                                );
                              },
                            ),
                          ),

                          // mini sparkline chart (visual hint)
                          SizedBox(
                            width: maxChartWidth,
                            height: 56,
                            child: Center(
                              child: Icon(Icons.show_chart,
                                  size: 28, color: Colors.grey[400]),
                            ),
                          ),
                        ],
                      ),
                    ],
                  );
                }),
              ),
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildMarketerBadge(Map<String, dynamic>? marketer) {
    if (marketer == null) return const SizedBox.shrink();

    final String name =
        (marketer['full_name']?.toString().trim().isNotEmpty == true)
            ? marketer['full_name'].toString().trim()
            : (marketer['name']?.toString().trim().isNotEmpty == true
                ? marketer['name'].toString().trim()
                : 'Not assigned');

    // Grab any of the commonly used keys and trim whitespace
    String? avatarUrl = (marketer['profile_image'] as String?)?.trim();
    avatarUrl ??= (marketer['avatar'] as String?)?.trim();
    avatarUrl ??= (marketer['image'] as String?)?.trim();

    bool _looksLikeAbsoluteUrl(String? s) {
      if (s == null || s.isEmpty) return false;
      final uri = Uri.tryParse(s);
      return uri != null &&
          (uri.hasScheme && (uri.scheme == 'http' || uri.scheme == 'https') ||
              s.startsWith('//'));
    }

    Widget avatarWidget;
    if (_looksLikeAbsoluteUrl(avatarUrl)) {
      avatarWidget = ClipOval(
        child: Image.network(
          avatarUrl!,
          width: 24,
          height: 24,
          fit: BoxFit.cover,
          loadingBuilder: (context, child, progress) {
            if (progress == null) return child;
            return SizedBox(
              width: 24,
              height: 24,
              child: Center(
                child: CircularProgressIndicator(
                  strokeWidth: 2,
                  value: progress.expectedTotalBytes != null
                      ? progress.cumulativeBytesLoaded /
                          (progress.expectedTotalBytes ?? 1)
                      : null,
                ),
              ),
            );
          },
          errorBuilder: (context, error, stackTrace) {
            // fallback to local asset if network fails
            return Image.asset('assets/avater.webp',
                width: 24, height: 24, fit: BoxFit.cover);
          },
        ),
      );
    } else {
      // Not an absolute URL -> use local asset fallback
      avatarWidget = ClipOval(
        child: Image.asset('assets/avater.webp',
            width: 24, height: 24, fit: BoxFit.cover),
      );
    }

    return AnimatedContainer(
      key: ValueKey(name),
      duration: const Duration(milliseconds: 520),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [Color(0xFF4154F1), Color(0xFF7F8CFF)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(24),
        boxShadow: [
          BoxShadow(
              color: Colors.black.withOpacity(0.1),
              blurRadius: 12,
              offset: const Offset(0, 6)),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          SizedBox(width: 24, height: 24, child: avatarWidget),
          const SizedBox(width: 8),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Your Marketer',
                style: GoogleFonts.sora(
                    fontSize: 10, color: Colors.white.withOpacity(0.9)),
              ),
              Text(
                name,
                style: GoogleFonts.sora(
                    fontSize: 12,
                    color: Colors.white,
                    fontWeight: FontWeight.w700),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildRankBadge(String rankTag) {
    // Define rank styling based on rank tier
    Map<String, dynamic> getRankStyle(String rank) {
      switch (rank) {
        case 'Royal Elite':
          return {
            'icon': Icons.diamond,
            'gradient': [const Color(0xFF6a11cb), const Color(0xFF2575fc)],
            'shadowColor': const Color(0xFF2575fc).withOpacity(0.25),
          };
        case 'Estate Ambassador':
          return {
            'icon': Icons.military_tech,
            'gradient': [const Color(0xFFfbbf24), const Color(0xFFf59e0b)],
            'shadowColor': const Color(0xFFf59e0b).withOpacity(0.25),
          };
        case 'Prime Investor':
          return {
            'icon': Icons.trending_up,
            'gradient': [const Color(0xFF3b82f6), const Color(0xFF06b6d4)],
            'shadowColor': const Color(0xFF06b6d4).withOpacity(0.25),
          };
        case 'Smart Owner':
          return {
            'icon': Icons.lightbulb,
            'gradient': [const Color(0xFF10b981), const Color(0xFF34d399)],
            'shadowColor': const Color(0xFF10b981).withOpacity(0.25),
          };
        case 'First-Time Investor':
        default:
          return {
            'icon': Icons.emoji_events,
            'gradient': [const Color(0xFF8b5cf6), const Color(0xFFa78bfa)],
            'shadowColor': const Color(0xFF8b5cf6).withOpacity(0.25),
          };
      }
    }

    final style = getRankStyle(rankTag);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: style['gradient'] as List<Color>,
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(10),
        boxShadow: [
          BoxShadow(
            color: style['shadowColor'] as Color,
            blurRadius: 12,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            style['icon'] as IconData,
            size: 14,
            color: Colors.white,
          ),
          const SizedBox(width: 6),
          Text(
            rankTag,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: GoogleFonts.sora(
              fontSize: 11,
              fontWeight: FontWeight.w700,
              color: Colors.white,
              letterSpacing: 0.3,
            ),
          ),
        ],
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
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Text(
                    'Contact Information',
                    style: GoogleFonts.sora(
                        fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const Spacer(),
                ],
              ),
              const SizedBox(height: 12),
              _buildContactItem(
                  icon: Icons.email_outlined,
                  label: 'Email',
                  value: email,
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: email));
                    ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Email copied to clipboard')));
                  }),
              _buildContactItem(
                  icon: Icons.phone_outlined,
                  label: 'Phone',
                  value: phone,
                  onTap: () {
                    Clipboard.setData(ClipboardData(text: phone));
                    ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Phone copied to clipboard')));
                  }),
              _buildContactItem(
                  icon: Icons.location_on_outlined,
                  label: 'Address',
                  value: address,
                  onTap: () {}),
              _buildContactItem(
                  icon: Icons.business_outlined,
                  label: 'Company',
                  value: company,
                  onTap: () {}),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContactItem({
    required IconData icon,
    required String label,
    required String value,
    GestureTapCallback? onTap,
  }) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8.0),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(10),
              decoration: BoxDecoration(
                color: const Color(0xFF4154F1).withOpacity(0.06),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(icon, size: 18, color: const Color(0xFF4154F1)),
            ),
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
                            fontSize: 14, fontWeight: FontWeight.w600)),
                  ]),
            ),
            if (onTap != null)
              Padding(
                padding: const EdgeInsets.only(left: 8.0),
                child: Icon(Icons.copy, size: 16, color: Colors.grey[400]),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildProfileDetails(Map<String, dynamic> profile) {
    final about = profile['about'] as String? ?? 'No information provided';
    final rawDate = profile['date_registered'];
    String dateRegistered;
    if (rawDate == null) {
      dateRegistered = 'Not specified';
    } else {
      final s = rawDate.toString();
      String datePart;
      if (s.contains('T')) {
        datePart = s.split('T')[0];
      } else if (s.contains(' ')) {
        datePart = s.split(' ')[0];
      } else {
        datePart = s;
      }
      try {
        final dt = DateTime.parse(datePart);
        dateRegistered = DateFormat.yMMMMd().format(dt);
      } catch (_) {
        dateRegistered = datePart;
      }
    }

    final country = profile['country']?.toString() ?? 'Not specified';
    final fullName = profile['full_name']?.toString() ?? 'Not specified';

    bool isLong = about.length > 140;
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
              offset: const Offset(0, 12),
            )
          ],
        ),
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: LayoutBuilder(
            builder: (context, constraints) {
              // determine columns based on available width
              final cols = constraints.maxWidth > 600 ? 3 : 2;
              const gap = 12.0;
              // tile width calculation accounts for gaps between items
              final tileWidth =
                  (constraints.maxWidth - (gap * (cols - 1))) / cols;

              return SingleChildScrollView(
                physics: const BouncingScrollPhysics(),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Text(
                          'About Me',
                          style: GoogleFonts.sora(
                            fontSize: 18,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                        const Spacer(),
                        IconButton(
                          onPressed: () {
                            // switch to Edit Profile tab (index 1)
                            _tabController.animateTo(1);
                          },
                          icon: const Icon(Icons.edit_outlined,
                              color: Color(0xFF4154F1)),
                        )
                      ],
                    ),
                    const SizedBox(height: 8),
                    AnimatedCrossFade(
                      firstChild: Text(
                        preview,
                        style: GoogleFonts.sora(
                          fontStyle: FontStyle.italic,
                          color: Colors.grey[700],
                        ),
                      ),
                      secondChild: Text(
                        about,
                        style: GoogleFonts.sora(
                          fontStyle: FontStyle.italic,
                          color: Colors.grey[800],
                        ),
                      ),
                      crossFadeState: about.length > 140
                          ? CrossFadeState.showFirst
                          : CrossFadeState.showSecond,
                      duration: const Duration(milliseconds: 450),
                    ),
                    if (isLong)
                      Align(
                        alignment: Alignment.centerLeft,
                        child: TextButton(
                          onPressed: () {
                            showDialog(
                              context: context,
                              builder: (ctx) => AlertDialog(
                                title:
                                    Text('About Me', style: GoogleFonts.sora()),
                                content: Text(about, style: GoogleFonts.sora()),
                                actions: [
                                  TextButton(
                                    onPressed: () => Navigator.of(ctx).pop(),
                                    child: Text(
                                      'Close',
                                      style: GoogleFonts.sora(),
                                    ),
                                  ),
                                ],
                              ),
                            );
                          },
                          child: Text(
                            'Read more',
                            style: GoogleFonts.sora(
                              color: const Color(0xFF4154F1),
                            ),
                          ),
                        ),
                      ),
                    const SizedBox(height: 12),
                    Text(
                      'Profile Details',
                      style: GoogleFonts.sora(
                        fontSize: 18,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                    const SizedBox(height: 12),
                    // Responsive wrap in place of GridView to avoid overflow and allow tile content to wrap
                    Wrap(
                      spacing: gap,
                      runSpacing: gap,
                      children: [
                        SizedBox(
                          width: tileWidth,
                          child: _buildInfoItem(
                              label: 'Full Name', value: fullName),
                        ),
                        SizedBox(
                          width: tileWidth,
                          child:
                              _buildInfoItem(label: 'Country', value: country),
                        ),
                        SizedBox(
                          width: tileWidth,
                          child: _buildInfoItem(
                              label: 'Date Registered', value: dateRegistered),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
                    _buildPortfolioSummaryCard(
                      propertiesCount: _toInt(profile['properties_count']),
                      totalValue: _toDouble(profile['total_value']),
                      currentValue: _toDouble(profile['current_value']),
                      appreciationTotal:
                          _toDouble(profile['appreciation_total']),
                    ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }

  Widget _buildInfoItem({required String label, required String value}) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.withOpacity(0.06)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label,
              style: GoogleFonts.sora(fontSize: 12, color: Colors.grey[600])),
          const SizedBox(height: 6),
          Text(value,
              style:
                  GoogleFonts.sora(fontSize: 14, fontWeight: FontWeight.w700)),
        ],
      ),
    );
  }

  Widget _buildPortfolioSummaryCard({
    required int propertiesCount,
    required double totalValue,
    required double currentValue,
    required double appreciationTotal,
  }) {
    // ensure values are finite and safe
    totalValue = totalValue.isFinite ? totalValue : 0.0;
    currentValue = currentValue.isFinite ? currentValue : 0.0;
    appreciationTotal = appreciationTotal.isFinite ? appreciationTotal : 0.0;

    final growthPercent = totalValue > 0
        ? ((currentValue - totalValue) / (totalValue) * 100)
            .clamp(-999.0, 9999.0)
        : 0.0;

    return Container(
      margin: const EdgeInsets.only(top: 8),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFF),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey.withOpacity(0.06)),
      ),
      child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text('Portfolio Summary',
            style: GoogleFonts.sora(fontSize: 16, fontWeight: FontWeight.bold)),
        const SizedBox(height: 12),
        _buildSummaryItem(
            label: 'Total Properties', value: propertiesCount.toString()),
        _buildSummaryItem(
            label: 'Total Investment',
            // value: '₦${totalValue.toStringAsFixed(2)}'),
            value: formatCurrency(totalValue, decimalDigits: 2)),
        _buildSummaryItem(
            label: 'Current Value',
            // value: '₦${currentValue.toStringAsFixed(2)}'),
            value: formatCurrency(currentValue, decimalDigits: 2)),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: LinearProgressIndicator(
                value: (currentValue > 0 && totalValue > 0)
                    ? (currentValue / (totalValue * 1.15)).clamp(0.0, 1.0)
                    : 0.0,
                minHeight: 8,
                backgroundColor: Colors.grey.withOpacity(0.12),
                valueColor: AlwaysStoppedAnimation<Color>(growthPercent >= 0
                    ? const Color(0xFF10B981)
                    : const Color(0xFFEF4444)),
              ),
            ),
            const SizedBox(width: 12),
            Column(crossAxisAlignment: CrossAxisAlignment.end, children: [
              Text(
                  growthPercent.isFinite
                      ? '${growthPercent.toStringAsFixed(2)}%'
                      : '0.00%',
                  style: GoogleFonts.sora(fontWeight: FontWeight.w700)),
              Text('growth',
                  style:
                      GoogleFonts.sora(fontSize: 12, color: Colors.grey[600])),
            ]),
          ],
        ),
        const SizedBox(height: 8),
        _buildSummaryItem(
            label: 'Total Appreciation',
            value: formatCurrency(appreciationTotal, decimalDigits: 2),
            isPositive: appreciationTotal >= 0),
      ]),
    );
  }

  Widget _buildSummaryItem({
    required String label,
    required dynamic value,
    bool isPositive = false,
    int? decimalDigits,
  }) {
    final formattedValue = value is String
        ? value
        : formatCurrency(value, decimalDigits: decimalDigits ?? 2);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6.0),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            label,
            style: GoogleFonts.roboto(fontSize: 13, color: Colors.grey[700]),
          ),
          Text(
            formattedValue,
            style: GoogleFonts.roboto(
              fontWeight: FontWeight.w800,
              color: isPositive
                  ? const Color(0xFF10B981)
                  : const Color(0xFF111827),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildShimmerLoader() {
    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        Shimmer.fromColors(
          baseColor: Colors.grey[300]!,
          highlightColor: Colors.grey[100]!,
          child: Container(
              height: 140,
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16))),
        ),
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
                        borderRadius: BorderRadius.circular(12)))),
          ]),
        ),
        const SizedBox(height: 14),
        Shimmer.fromColors(
          baseColor: Colors.grey[300]!,
          highlightColor: Colors.grey[100]!,
          child: Container(
              height: 220,
              decoration: BoxDecoration(
                  color: Colors.white,
                  borderRadius: BorderRadius.circular(16))),
        ),
      ],
    );
  }
}

class _SliverAppBarDelegate extends SliverPersistentHeaderDelegate {
  final TabBar _tabBar;

  _SliverAppBarDelegate(this._tabBar);

  @override
  Widget build(
      BuildContext context, double shrinkOffset, bool overlapsContent) {
    return Container(
      color: Colors.white,
      child: _tabBar,
    );
  }

  @override
  double get maxExtent => _tabBar.preferredSize.height;

  @override
  double get minExtent => _tabBar.preferredSize.height;

  @override
  bool shouldRebuild(_SliverAppBarDelegate oldDelegate) {
    return false;
  }
}
