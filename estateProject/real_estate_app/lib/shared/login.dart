import 'dart:async';
import 'dart:ui';
import 'dart:math' as math;
import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:real_estate_app/core/credential_storage.dart';
import 'package:real_estate_app/core/api_service.dart';
import 'package:real_estate_app/admin/admin_dashboard.dart';
import 'package:real_estate_app/client/client_dashboard.dart';
import 'package:real_estate_app/marketer/marketer_dashboard.dart';
import 'package:real_estate_app/services/navigation_service.dart';
import 'package:real_estate_app/services/push_notification_service.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with TickerProviderStateMixin {
  static const Color primaryColor = Color(0xFF5E35B1);
  // Form
  final _formKey = GlobalKey<FormState>();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  // Error holders (for inline display)
  String? _generalError;
  String? _emailError;
  String? _passwordError;
  // Role selection state for multi-role accounts
  List<dynamic>? _roleSelectionUsers;
  int? _selectedUserId;

  // Animations
  late final AnimationController _cardController;
  late final Animation<double> _opacityAnim;
  late final Animation<Offset> _slideAnim;
  late final Animation<double> _scaleAnim;

  late final AnimationController _bgController; // background + button pulse

  bool _loading = false;
  bool _rememberMe = false;
  bool _obscurePassword = true;

  @override
  void initState() {
    super.initState();

    // Card animations
    _cardController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 900),
    );
    _opacityAnim =
        CurvedAnimation(parent: _cardController, curve: Curves.easeIn);
    _slideAnim = Tween<Offset>(begin: const Offset(0, 0.06), end: Offset.zero)
        .animate(
            CurvedAnimation(parent: _cardController, curve: Curves.easeOut));
    _scaleAnim = Tween<double>(begin: 0.98, end: 1.0).animate(
        CurvedAnimation(parent: _cardController, curve: Curves.elasticOut));
    _cardController.forward();

    // Background / pulse animation (loop)
    _bgController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    // Load saved credentials
    _loadRemembered();
  }

  Future<void> _loadRemembered() async {
    try {
      final remember = await CredentialStorage.read('remember_me');
      if (remember != null && remember == 'true') {
        final savedEmail = await CredentialStorage.read('saved_email');
        final savedPassword = await CredentialStorage.read('saved_password');
        setState(() {
          _rememberMe = true;
          if (savedEmail != null) _emailController.text = savedEmail;
          if (savedPassword != null) _passwordController.text = savedPassword;
        });
      }
    } catch (_) {
      // ignore read errors
    }
  }

  Future<void> _saveRemembered() async {
    try {
      if (_rememberMe) {
        await CredentialStorage.write('remember_me', 'true');
        await CredentialStorage.write(
            'saved_email', _emailController.text.trim());
        await CredentialStorage.write(
            'saved_password', _passwordController.text);
      } else {
        await CredentialStorage.write('remember_me', 'false');
        await CredentialStorage.delete('saved_email');
        await CredentialStorage.delete('saved_password');
      }
    } catch (_) {
      // ignore write errors
    }
  }

  @override
  void dispose() {
    _cardController.dispose();
    _bgController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  String _parseErrorMessage(Object error) {
    try {
      final s = error.toString();
      final start = s.indexOf('{');
      final end = s.lastIndexOf('}');
      if (start != -1 && end != -1 && end > start) {
        final jsonStr = s.substring(start, end + 1);
        final data = jsonDecode(jsonStr);
        if (data is Map) {
          if (data.containsKey('non_field_errors')) {
            final v = data['non_field_errors'];
            if (v is List) return v.join(' ');
            return v.toString();
          }
          if (data.containsKey('detail')) return data['detail'].toString();
          final parts = <String>[];
          data.forEach((k, v) {
            if (v is List)
              parts.addAll(v.map((e) => e.toString()));
            else
              parts.add(v.toString());
          });
          if (parts.isNotEmpty) return parts.join(' ');
        }
      }
    } catch (_) {}
    return error.toString();
  }

  Future<int?> _showRoleSelectionDialog(List<dynamic> users) async {
    int? selectedUserId;
    return showDialog<int>(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setStateDialog) {
            return AlertDialog(
              title: const Text('Select role'),
              content: SizedBox(
                width: double.maxFinite,
                child: ListView.builder(
                  shrinkWrap: true,
                  itemCount: users.length,
                  itemBuilder: (context, index) {
                    final u = users[index];
                    if (u is! Map) return const SizedBox.shrink();

                    final id = u['id'];
                    final role = (u['role'] ?? '').toString();
                    final fullName = (u['full_name'] ?? '').toString();
                    final company = u['company'];
                    String companyLabel = '';
                    if (company is Map) {
                      final name = (company['name'] ?? '').toString();
                      final slug = (company['slug'] ?? '').toString();
                      companyLabel = name.isNotEmpty
                          ? (slug.isNotEmpty ? '$name ($slug)' : name)
                          : '';
                    }

                    final subtitleParts = <String>[];
                    if (fullName.isNotEmpty) subtitleParts.add(fullName);
                    if (companyLabel.isNotEmpty)
                      subtitleParts.add(companyLabel);

                    return RadioListTile<int>(
                      value:
                          (id is int) ? id : int.tryParse(id.toString()) ?? -1,
                      groupValue: selectedUserId,
                      onChanged: (val) {
                        setStateDialog(() {
                          selectedUserId = val;
                        });
                      },
                      title: Text(role.isEmpty ? 'User' : role),
                      subtitle: subtitleParts.isEmpty
                          ? null
                          : Text(subtitleParts.join(' • ')),
                    );
                  },
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context, null),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: selectedUserId == null
                      ? null
                      : () => Navigator.pop(context, selectedUserId),
                  child: const Text('Continue'),
                ),
              ],
            );
          },
        );
      },
    );
  }

  Future<void> _handleLogin() async {
    // Reset previous errors
    setState(() {
      _generalError = null;
      _emailError = null;
      _passwordError = null;
    });

    if (!_formKey.currentState!.validate()) return;

    setState(() {
      _loading = true;
    });

    await _saveRemembered();

    try {
      final email = _emailController.text.trim();
      final password = _passwordController.text;

      Map<String, dynamic> loginResp =
          await ApiService().loginUnified(email, password);

      // Handle server asking for role selection. Instead of forcing a dialog,
      // present an inline selection UI so mobile users can choose without
      // leaving the page. Keep dialog fallback for older flows.
      if (loginResp['requires_role_selection'] == true) {
        final multipleUsers = loginResp['multiple_users'];
        if (multipleUsers is List && multipleUsers.isNotEmpty) {
          setState(() {
            _roleSelectionUsers = multipleUsers;
            _selectedUserId = null;
            _loading = false; // stop spinner while selecting
          });
          // Wait for user to pick and continue (UI will show Continue button)
          return;
        } else {
          throw Exception('Multiple roles detected but no users returned.');
        }
      }

      final token = (loginResp['token'] ?? '').toString();
      if (token.isEmpty) {
        throw Exception('Login failed: missing token.');
      }

      Map<String, dynamic> profile;
      final respUser = loginResp['user'];
      if (respUser is Map<String, dynamic>) {
        profile = respUser;
      } else {
        profile = await ApiService().getUserProfile(token);
      }

      await NavigationService.storeUserToken(token);
      await PushNotificationService().syncTokenWithBackend();

      final role = (profile['role'] ?? '').toString().toLowerCase();

      if (role == 'admin_support' || role == 'support') {
        Navigator.pushReplacementNamed(context, '/admin-support-dashboard',
            arguments: token);
      } else if (role == 'admin') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => AdminDashboard(token: token)),
        );
      } else if (role == 'client') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => ClientDashboard(token: token)),
        );
      } else if (role == 'marketer') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => MarketerDashboard(token: token)),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('User role is not defined.')),
        );
      }
    } catch (e) {
      try {
        final s = e.toString();
        final start = s.indexOf('{');
        final end = s.lastIndexOf('}');
        if (start != -1 && end != -1 && end > start) {
          final jsonStr = s.substring(start, end + 1);
          final data = jsonDecode(jsonStr);
          if (data is Map) {
            setState(() {
              if (data.containsKey('email')) {
                final v = data['email'];
                _emailError = v is List ? v.join(' ') : v.toString();
              }
              if (data.containsKey('password')) {
                final v = data['password'];
                _passwordError = v is List ? v.join(' ') : v.toString();
              }
              if (data.containsKey('non_field_errors')) {
                final v = data['non_field_errors'];
                _generalError = v is List ? v.join(' ') : v.toString();
              } else if (_generalError == null) {
                _generalError = _parseErrorMessage(e);
              }
            });
          } else {
            setState(() {
              _generalError = _parseErrorMessage(e);
            });
          }
        } else {
          setState(() {
            _generalError = _parseErrorMessage(e);
          });
        }
      } catch (_) {
        setState(() {
          _generalError = _parseErrorMessage(e);
        });
      }

      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(_generalError ?? 'Login failed: ${e.toString()}'),
        ),
      );
    } finally {
      if (mounted) {
        setState(() {
          _loading = false;
        });
      }
    }
  }

  // Submit selected role when inline role-selection UI is shown
  Future<void> _continueWithSelectedRole() async {
    if (_selectedUserId == null) return;

    setState(() {
      _loading = true;
      _generalError = null;
      _emailError = null;
      _passwordError = null;
    });

    try {
      final email = _emailController.text.trim();
      final password = _passwordController.text;

      final loginResp = await ApiService().loginUnified(
        email,
        password,
        selectedUserId: _selectedUserId,
      );

      final token = (loginResp['token'] ?? '').toString();
      if (token.isEmpty) throw Exception('Login failed: missing token.');

      Map<String, dynamic> profile;
      final respUser = loginResp['user'];
      if (respUser is Map<String, dynamic>) {
        profile = respUser;
      } else {
        profile = await ApiService().getUserProfile(token);
      }

      await NavigationService.storeUserToken(token);
      await PushNotificationService().syncTokenWithBackend();

      setState(() {
        _roleSelectionUsers = null;
        _selectedUserId = null;
      });

      final role = (profile['role'] ?? '').toString().toLowerCase();
      if (role == 'admin_support' || role == 'support') {
        Navigator.pushReplacementNamed(context, '/admin-support-dashboard',
            arguments: token);
      } else if (role == 'admin') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => AdminDashboard(token: token)),
        );
      } else if (role == 'client') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => ClientDashboard(token: token)),
        );
      } else if (role == 'marketer') {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => MarketerDashboard(token: token)),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('User role is not defined.')),
        );
      }
    } catch (e) {
      setState(() {
        _generalError = _parseErrorMessage(e);
      });
      ScaffoldMessenger.of(context)
          .showSnackBar(SnackBar(content: Text(_generalError ?? e.toString())));
    } finally {
      if (mounted)
        setState(() {
          _loading = false;
        });
    }
  }

  Future<void> _showForgotPasswordDialog() async {
    final _fpController =
        TextEditingController(text: _emailController.text.trim());
    await showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Reset Password'),
          content: TextFormField(
            controller: _fpController,
            keyboardType: TextInputType.emailAddress,
            decoration: const InputDecoration(
              labelText: 'Enter your email',
              prefixIcon: Icon(Icons.email_outlined),
            ),
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel')),
            ElevatedButton(
              onPressed: () async {
                final email = _fpController.text.trim();
                if (email.isEmpty) {
                  ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Please enter your email')));
                  return;
                }
                Navigator.pop(context);
                try {
                  await ApiService().requestPasswordReset(email);
                  ScaffoldMessenger.of(context).showSnackBar(const SnackBar(
                      content: Text('Password reset link sent.')));
                } catch (e) {
                  try {
                    Navigator.pushNamed(context, '/forgot-password',
                        arguments: {'email': email});
                  } catch (_) {
                    ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text('Failed to request reset: $e')));
                  }
                }
              },
              child: const Text('Send'),
            ),
          ],
        );
      },
    );
  }

  // -----------------------------
  // Registration UI dialogs
  // -----------------------------
  Future<void> _showAccountTypeDialog() async {
    await showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Create Your Account'),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Text('Choose your account type'),
              const SizedBox(height: 12),
              ElevatedButton.icon(
                icon: const Icon(Icons.person),
                label: const Text('Client'),
                onPressed: () {
                  Navigator.pop(context);
                  _showClientRegistrationDialog();
                },
              ),
              const SizedBox(height: 8),
              ElevatedButton.icon(
                icon: const Icon(Icons.handshake),
                label: const Text('Affiliate / Marketer'),
                onPressed: () {
                  Navigator.pop(context);
                  _showMarketerRegistrationDialog();
                },
              ),
            ],
          ),
          actions: [
            TextButton(
                onPressed: () => Navigator.pop(context),
                child: const Text('Cancel')),
          ],
        );
      },
    );
  }

  Future<void> _showClientRegistrationDialog() async {
    final _formKey = GlobalKey<FormState>();
    final first = TextEditingController();
    final last = TextEditingController();
    final email = TextEditingController();
    final phone = TextEditingController();
    final address = TextEditingController();
    DateTime? dob;
    final password = TextEditingController();
    final confirm = TextEditingController();
    var loading = false;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(builder: (context, setStateDialog) {
          return AlertDialog(
            title: const Text('Client Registration'),
            content: SingleChildScrollView(
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: first,
                      decoration:
                          const InputDecoration(labelText: 'First Name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: last,
                      decoration: const InputDecoration(labelText: 'Last Name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: email,
                      decoration: const InputDecoration(labelText: 'Email'),
                      keyboardType: TextInputType.emailAddress,
                      validator: (v) => (v == null ||
                              !RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v))
                          ? 'Enter valid email'
                          : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: phone,
                      decoration: const InputDecoration(labelText: 'Phone'),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: address,
                      decoration: const InputDecoration(labelText: 'Address'),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                            child: Text(dob == null
                                ? 'Date of birth: Not set'
                                : 'DOB: ${dob.toString().split(' ').first}')),
                        TextButton(
                          onPressed: () async {
                            final d = await showDatePicker(
                              context: context,
                              initialDate: DateTime(1990, 1, 1),
                              firstDate: DateTime(1900),
                              lastDate: DateTime.now(),
                            );
                            if (d != null) setStateDialog(() => dob = d);
                          },
                          child: const Text('Select'),
                        )
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: password,
                      decoration: const InputDecoration(labelText: 'Password'),
                      obscureText: true,
                      validator: (v) =>
                          (v == null || v.length < 8) ? 'Min 8 chars' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: confirm,
                      decoration:
                          const InputDecoration(labelText: 'Confirm Password'),
                      obscureText: true,
                      validator: (v) => (v != password.text)
                          ? 'Passwords do not match'
                          : null,
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel')),
              ElevatedButton(
                onPressed: loading
                    ? null
                    : () async {
                        if (!_formKey.currentState!.validate()) return;
                        setStateDialog(() => loading = true);
                        try {
                          final payload = {
                            'first_name': first.text.trim(),
                            'last_name': last.text.trim(),
                            'email': email.text.trim(),
                            'phone': phone.text.trim(),
                            'address': address.text.trim(),
                            'date_of_birth': dob == null
                                ? ''
                                : dob!.toIso8601String().split('T').first,
                            'password': password.text,
                            'confirm_password': confirm.text,
                            // security tracking fields
                            'timezone': DateTime.now().timeZoneName,
                            'screen_res':
                                '${MediaQuery.of(context).size.width}x${MediaQuery.of(context).size.height}',
                          };
                          final resp =
                              await ApiService().registerClient(payload);
                          final message = resp['message'] ??
                              'Client registered successfully';
                          Navigator.pop(context);
                          ScaffoldMessenger.of(this.context)
                              .showSnackBar(SnackBar(content: Text(message)));
                          // Pre-fill login email
                          setState(
                              () => _emailController.text = email.text.trim());
                        } catch (e) {
                          setStateDialog(() => loading = false);
                          ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(
                                  content: Text('Failed: ${e.toString()}')));
                        }
                      },
                child: loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Create Client Account'),
              )
            ],
          );
        });
      },
    );
  }

  Future<void> _showMarketerRegistrationDialog() async {
    final _formKey = GlobalKey<FormState>();
    final first = TextEditingController();
    final last = TextEditingController();
    final email = TextEditingController();
    final phone = TextEditingController();
    final address = TextEditingController();
    DateTime? dob;
    final password = TextEditingController();
    final confirm = TextEditingController();
    var loading = false;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(builder: (context, setStateDialog) {
          return AlertDialog(
            title: const Text('Affiliate / Marketer Registration'),
            content: SingleChildScrollView(
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: first,
                      decoration:
                          const InputDecoration(labelText: 'First Name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: last,
                      decoration: const InputDecoration(labelText: 'Last Name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: email,
                      decoration: const InputDecoration(labelText: 'Email'),
                      keyboardType: TextInputType.emailAddress,
                      validator: (v) => (v == null ||
                              !RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v))
                          ? 'Enter valid email'
                          : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: phone,
                      decoration: const InputDecoration(labelText: 'Phone'),
                      keyboardType: TextInputType.phone,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: address,
                      decoration: const InputDecoration(labelText: 'Address'),
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                            child: Text(dob == null
                                ? 'Date of birth: Not set'
                                : 'DOB: ${dob.toString().split(' ').first}')),
                        TextButton(
                          onPressed: () async {
                            final d = await showDatePicker(
                              context: context,
                              initialDate: DateTime(1990, 1, 1),
                              firstDate: DateTime(1900),
                              lastDate: DateTime.now(),
                            );
                            if (d != null) setStateDialog(() => dob = d);
                          },
                          child: const Text('Select'),
                        )
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: password,
                      decoration: const InputDecoration(labelText: 'Password'),
                      obscureText: true,
                      validator: (v) =>
                          (v == null || v.length < 8) ? 'Min 8 chars' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: confirm,
                      decoration:
                          const InputDecoration(labelText: 'Confirm Password'),
                      obscureText: true,
                      validator: (v) => (v != password.text)
                          ? 'Passwords do not match'
                          : null,
                    ),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel')),
              ElevatedButton(
                onPressed: loading
                    ? null
                    : () async {
                        if (!_formKey.currentState!.validate()) return;
                        setStateDialog(() => loading = true);
                        try {
                          final payload = {
                            'first_name': first.text.trim(),
                            'last_name': last.text.trim(),
                            'email': email.text.trim(),
                            'phone': phone.text.trim(),
                            'address': address.text.trim(),
                            'date_of_birth': dob == null
                                ? ''
                                : dob!.toIso8601String().split('T').first,
                            'password': password.text,
                            'confirm_password': confirm.text,
                            // security tracking fields
                            'timezone': DateTime.now().timeZoneName,
                            'screen_res':
                                '${MediaQuery.of(context).size.width}x${MediaQuery.of(context).size.height}',
                          };
                          final resp =
                              await ApiService().registerMarketer(payload);
                          final message = resp['message'] ??
                              'Marketer registered successfully';
                          Navigator.pop(context);
                          ScaffoldMessenger.of(this.context)
                              .showSnackBar(SnackBar(content: Text(message)));
                          setState(
                              () => _emailController.text = email.text.trim());
                        } catch (e) {
                          setStateDialog(() => loading = false);
                          ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(
                                  content: Text('Failed: ${e.toString()}')));
                        }
                      },
                child: loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Create Marketer Account'),
              )
            ],
          );
        });
      },
    );
  }

  Future<void> _showCompanyRegistrationDialog() async {
    final _formKey = GlobalKey<FormState>();
    final companyName = TextEditingController();
    final regNumber = TextEditingController();
    DateTime? regDate;
    final location = TextEditingController();
    final ceoName = TextEditingController();
    DateTime? ceoDob;
    final email = TextEditingController();
    final phone = TextEditingController();
    String subscriptionTier = 'starter';
    final password = TextEditingController();
    final confirm = TextEditingController();
    final secondaryEmail = TextEditingController();
    final secondaryPhone = TextEditingController();
    final secondaryName = TextEditingController();
    var loading = false;

    await showDialog(
      context: context,
      barrierDismissible: false,
      builder: (context) {
        return StatefulBuilder(builder: (context, setStateDialog) {
          return AlertDialog(
            title: const Text('Register Company'),
            content: SingleChildScrollView(
              child: Form(
                key: _formKey,
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    TextFormField(
                      controller: companyName,
                      decoration:
                          const InputDecoration(labelText: 'Company Name'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: regNumber,
                      decoration: const InputDecoration(
                          labelText: 'Registration Number'),
                      validator: (v) =>
                          (v == null || v.trim().isEmpty) ? 'Required' : null,
                    ),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                            child: Text(regDate == null
                                ? 'Registration date: Not set'
                                : 'Date: ${regDate.toString().split(' ').first}')),
                        TextButton(
                            onPressed: () async {
                              final d = await showDatePicker(
                                  context: context,
                                  initialDate: DateTime.now(),
                                  firstDate: DateTime(1900),
                                  lastDate: DateTime.now());
                              if (d != null) setStateDialog(() => regDate = d);
                            },
                            child: const Text('Select'))
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: location,
                        decoration:
                            const InputDecoration(labelText: 'Location')),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: ceoName,
                        decoration:
                            const InputDecoration(labelText: 'CEO Full Name')),
                    const SizedBox(height: 8),
                    Row(
                      children: [
                        Expanded(
                            child: Text(ceoDob == null
                                ? 'CEO DOB: Not set'
                                : 'DOB: ${ceoDob.toString().split(' ').first}')),
                        TextButton(
                            onPressed: () async {
                              final d = await showDatePicker(
                                  context: context,
                                  initialDate: DateTime(1980, 1, 1),
                                  firstDate: DateTime(1900),
                                  lastDate: DateTime.now());
                              if (d != null) setStateDialog(() => ceoDob = d);
                            },
                            child: const Text('Select'))
                      ],
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                      controller: email,
                      decoration:
                          const InputDecoration(labelText: 'Company Email'),
                      keyboardType: TextInputType.emailAddress,
                      validator: (v) => (v == null ||
                              !RegExp(r'^[^@]+@[^@]+\.[^@]+').hasMatch(v))
                          ? 'Enter valid email'
                          : null,
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: phone,
                        decoration:
                            const InputDecoration(labelText: 'Company Phone'),
                        keyboardType: TextInputType.phone),
                    const SizedBox(height: 8),
                    DropdownButtonFormField<String>(
                      value: subscriptionTier,
                      items: const [
                        DropdownMenuItem(
                            value: 'starter', child: Text('Starter')),
                        DropdownMenuItem(
                            value: 'professional', child: Text('Professional')),
                        DropdownMenuItem(
                            value: 'enterprise', child: Text('Enterprise')),
                      ],
                      onChanged: (v) => setStateDialog(
                          () => subscriptionTier = v ?? 'starter'),
                      decoration:
                          const InputDecoration(labelText: 'Subscription Plan'),
                    ),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: password,
                        decoration:
                            const InputDecoration(labelText: 'Password'),
                        obscureText: true,
                        validator: (v) =>
                            (v == null || v.length < 8) ? 'Min 8 chars' : null),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: confirm,
                        decoration: const InputDecoration(
                            labelText: 'Confirm Password'),
                        obscureText: true,
                        validator: (v) => (v != password.text)
                            ? 'Passwords do not match'
                            : null),
                    const SizedBox(height: 8),
                    const Divider(),
                    const SizedBox(height: 8),
                    Text('Secondary Admin (optional)',
                        style: TextStyle(fontWeight: FontWeight.w600)),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: secondaryName,
                        decoration: const InputDecoration(
                            labelText: 'Secondary Admin Name')),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: secondaryEmail,
                        decoration: const InputDecoration(
                            labelText: 'Secondary Admin Email')),
                    const SizedBox(height: 8),
                    TextFormField(
                        controller: secondaryPhone,
                        decoration: const InputDecoration(
                            labelText: 'Secondary Admin Phone')),
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel')),
              ElevatedButton(
                onPressed: loading
                    ? null
                    : () async {
                        if (!_formKey.currentState!.validate()) return;
                        setStateDialog(() => loading = true);
                        try {
                          final payload = {
                            'company_name': companyName.text.trim(),
                            'registration_number': regNumber.text.trim(),
                            'registration_date': regDate == null
                                ? ''
                                : regDate!.toIso8601String().split('T').first,
                            'location': location.text.trim(),
                            'ceo_name': ceoName.text.trim(),
                            'ceo_dob': ceoDob == null
                                ? ''
                                : ceoDob!.toIso8601String().split('T').first,
                            'email': email.text.trim(),
                            'phone': phone.text.trim(),
                            'subscription_tier': subscriptionTier,
                            // password fields
                            'password': password.text,
                            'confirm_password': confirm.text,
                            // optional secondary admin
                            'secondary_admin_email': secondaryEmail.text.trim(),
                            'secondary_admin_phone': secondaryPhone.text.trim(),
                            'secondary_admin_name': secondaryName.text.trim(),
                            // security tracking fields
                            'timezone': DateTime.now().timeZoneName,
                            'screen_res':
                                '${MediaQuery.of(context).size.width}x${MediaQuery.of(context).size.height}',
                          };

                          final resp =
                              await ApiService().registerCompany(payload);
                          Navigator.pop(context);
                          final message = resp['message'] ??
                              'Company registered successfully';
                          ScaffoldMessenger.of(this.context)
                              .showSnackBar(SnackBar(content: Text(message)));
                          // Prefill login email
                          setState(
                              () => _emailController.text = email.text.trim());
                        } catch (e) {
                          setStateDialog(() => loading = false);
                          ScaffoldMessenger.of(this.context).showSnackBar(
                              SnackBar(
                                  content: Text('Failed: ${e.toString()}')));
                        }
                      },
                child: loading
                    ? const SizedBox(
                        width: 18,
                        height: 18,
                        child: CircularProgressIndicator(strokeWidth: 2))
                    : const Text('Create Company Account'),
              )
            ],
          );
        });
      },
    );
  }

  Widget _buildAnimatedBackground(Size size) {
    return AnimatedBuilder(
      animation: _bgController,
      builder: (context, child) {
        final t = _bgController.value;
        final double x1 =
            (size.width * 0.08) + (size.width * 0.08) * (0.5 + 0.5 * (t));
        final double y1 =
            (size.height * 0.08) + (size.height * 0.04) * (0.5 + 0.5 * (t));
        final double x2 = (size.width * 0.7) - (size.width * 0.1) * (t);
        final double y2 = (size.height * 0.68) - (size.height * 0.06) * (t);

        return Stack(
          children: [
            Positioned(
              left: x1.clamp(0.0, size.width),
              top: y1.clamp(0.0, size.height),
              child: Transform.rotate(
                angle: t * 1.8,
                child: Container(
                  width: size.width * 0.58,
                  height: size.width * 0.58,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.teal.shade700.withOpacity(0.14),
                        Colors.cyan.shade600.withOpacity(0.10),
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(240),
                  ),
                ),
              ),
            ),
            Positioned(
              left: x2.clamp(0.0, size.width),
              top: y2.clamp(0.0, size.height),
              child: Transform.rotate(
                angle: -t * 1.1,
                child: Container(
                  width: size.width * 0.46,
                  height: size.width * 0.46,
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        Colors.indigo.shade600.withOpacity(0.10),
                        Colors.deepPurple.shade600.withOpacity(0.09),
                      ],
                      begin: Alignment.topRight,
                      end: Alignment.bottomLeft,
                    ),
                    borderRadius: BorderRadius.circular(180),
                  ),
                ),
              ),
            ),
            Positioned.fill(
              child: IgnorePointer(
                child: Container(
                  decoration: BoxDecoration(
                    gradient: RadialGradient(
                      colors: [
                        Colors.transparent,
                        Colors.black.withOpacity(0.18),
                      ],
                      radius: 0.9,
                      center: const Alignment(0.0, 0.0),
                    ),
                  ),
                ),
              ),
            ),
          ],
        );
      },
    );
  }

  Widget _animatedSignInButton(
      {required VoidCallback onPressed, required bool loading}) {
    return AnimatedBuilder(
      animation: _bgController,
      builder: (context, child) {
        final sineWave =
            0.5 + 0.5 * math.sin(_bgController.value * 2 * math.pi);
        final glow = 6 + 6 * sineWave;
        final scale = 1.0 + 0.02 * sineWave;

        return Center(
          child: Transform.scale(
            scale: scale,
            child: Material(
              color: Colors.transparent,
              child: InkWell(
                onTap: loading ? null : onPressed,
                borderRadius: BorderRadius.circular(14),
                splashFactory: InkRipple.splashFactory,
                child: Container(
                  height: 56,
                  padding: const EdgeInsets.symmetric(horizontal: 20),
                  decoration: BoxDecoration(
                    gradient: LinearGradient(
                      colors: [
                        primaryColor.withOpacity(0.98),
                        primaryColor.withOpacity(0.78)
                      ],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(14),
                    boxShadow: [
                      BoxShadow(
                        color: Colors.cyan.withOpacity(0.18),
                        blurRadius: glow,
                        spreadRadius: 0.6,
                        offset: const Offset(0, 6),
                      ),
                    ],
                  ),
                  child: Row(
                    mainAxisSize: MainAxisSize.min,
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      if (!loading) ...[
                        const Icon(Icons.login_rounded, color: Colors.white),
                        const SizedBox(width: 12),
                        const Text(
                          'Sign In',
                          style: TextStyle(
                            color: Colors.white,
                            fontWeight: FontWeight.w800,
                            fontSize: 16,
                          ),
                        ),
                      ] else ...[
                        const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(
                              strokeWidth: 2.5, color: Colors.white),
                        ),
                        const SizedBox(width: 12),
                        const Text(
                          'Signing in...',
                          style: TextStyle(
                            color: Colors.white70,
                            fontWeight: FontWeight.w700,
                            fontSize: 15,
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final mq = MediaQuery.of(context);
    final size = mq.size;
    // Detect keyboard
    final bottomInset = mq.viewInsets.bottom;
    final keyboardOpen = bottomInset > 0.0;

    return Scaffold(
      // Prevent Scaffold from resizing when keyboard appears to avoid leaving gaps
      resizeToAvoidBottomInset: false,

      extendBodyBehindAppBar: true,
      body: Stack(
        children: [
          // dark moody gradient
          Container(
            decoration: BoxDecoration(
              gradient: LinearGradient(
                colors: [
                  const Color(0xFF0B1020),
                  Colors.blueGrey.shade900,
                ],
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
              ),
            ),
          ),

          // animated blobs
          _buildAnimatedBackground(size),

          // glass blur layer: reduce / remove blur when keyboard is open to avoid keyboard/blur artifact
          Positioned.fill(
            child: BackdropFilter(
              filter: ImageFilter.blur(
                sigmaX: keyboardOpen ? 4.0 : 12.0,
                sigmaY: keyboardOpen ? 4.0 : 12.0,
              ),
              // Use a fully transparent overlay while keyboard is open to avoid visible banding.
              child: Container(
                color: keyboardOpen
                    ? Colors.transparent
                    : Colors.black.withOpacity(0.02),
              ),
            ),
          ),

          SafeArea(
            child: LayoutBuilder(builder: (context, constraints) {
              final maxWidth = constraints.maxWidth > 700
                  ? 560.0
                  : constraints.maxWidth * 0.94;
              return Center(
                child: SingleChildScrollView(
                  // Add bottom padding matching keyboard height so content can scroll above keyboard.
                  padding: EdgeInsets.only(
                    left: 16,
                    right: 16,
                    top: 26,
                    bottom: 26 + bottomInset,
                  ),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Back button
                      Row(
                        children: [
                          IconButton(
                            onPressed: () => Navigator.pushNamed(context, '/'),
                            icon: const Icon(Icons.arrow_back_ios_new),
                            color: Colors.white70,
                            tooltip: 'Back',
                          ),
                        ],
                      ),

                      const SizedBox(height: 8),

                      // frosted card
                      ConstrainedBox(
                        constraints: BoxConstraints(maxWidth: maxWidth),
                        child: FadeTransition(
                          opacity: _opacityAnim,
                          child: SlideTransition(
                            position: _slideAnim,
                            child: ScaleTransition(
                              scale: _scaleAnim,
                              child: ClipRRect(
                                borderRadius: BorderRadius.circular(20),
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                      horizontal: 28, vertical: 26),
                                  decoration: BoxDecoration(
                                    color: Colors.white.withOpacity(0.06),
                                    borderRadius: BorderRadius.circular(20),
                                    border: Border.all(
                                        color: Colors.white.withOpacity(0.08),
                                        width: 1.0),
                                    boxShadow: [
                                      BoxShadow(
                                        color: Colors.black.withOpacity(0.28),
                                        blurRadius: 24,
                                        offset: const Offset(0, 12),
                                      ),
                                    ],
                                  ),
                                  child: Form(
                                    key: _formKey,
                                    child: Column(
                                        mainAxisSize: MainAxisSize.min,
                                        crossAxisAlignment:
                                            CrossAxisAlignment.stretch,
                                        children: [
                                          // Lamba logo box + header text (matches web)
                                          Hero(
                                            tag: 'app-logo',
                                            child: Row(
                                              children: [
                                                Container(
                                                  height: 74,
                                                  width: 74,
                                                  decoration: BoxDecoration(
                                                    borderRadius:
                                                        BorderRadius.circular(
                                                            18),
                                                    gradient:
                                                        const LinearGradient(
                                                      colors: [
                                                        Color(0xFF667EEA),
                                                        Color(0xFF764BA2)
                                                      ],
                                                      begin: Alignment.topLeft,
                                                      end:
                                                          Alignment.bottomRight,
                                                    ),
                                                    boxShadow: [
                                                      BoxShadow(
                                                        color: const Color(
                                                                0xFF667EEA)
                                                            .withOpacity(0.25),
                                                        blurRadius: 20,
                                                        offset:
                                                            const Offset(0, 8),
                                                      )
                                                    ],
                                                  ),
                                                  child: const Center(
                                                    child: Icon(Icons.shield,
                                                        color: Colors.white,
                                                        size: 28),
                                                  ),
                                                ),
                                                const SizedBox(width: 12),
                                                Expanded(
                                                  child: Column(
                                                    crossAxisAlignment:
                                                        CrossAxisAlignment
                                                            .start,
                                                    children: const [
                                                      Text(
                                                        'Lamba Login',
                                                        style: TextStyle(
                                                          color: Colors.white,
                                                          fontSize: 20,
                                                          fontWeight:
                                                              FontWeight.w900,
                                                        ),
                                                      ),
                                                      SizedBox(height: 4),
                                                      Text(
                                                        'Secure access for Company Admins, Clients & Marketers',
                                                        style: TextStyle(
                                                          color: Colors.white70,
                                                          fontSize: 13,
                                                        ),
                                                      ),
                                                    ],
                                                  ),
                                                ),
                                              ],
                                            ),
                                          ),

                                          const SizedBox(height: 12),

                                          // If the server returned multiple user roles,
                                          // show an inline role-selection UI.
                                          if (_roleSelectionUsers != null) ...[
                                            Column(
                                              crossAxisAlignment:
                                                  CrossAxisAlignment.stretch,
                                              children: [
                                                const Text(
                                                  'Multiple accounts found — select a role to continue',
                                                  style: TextStyle(
                                                      color: Colors.white70,
                                                      fontWeight:
                                                          FontWeight.w700),
                                                ),
                                                const SizedBox(height: 10),
                                                ..._roleSelectionUsers!
                                                    .map((u) {
                                                  final id = u['id'];
                                                  final role = (u['role'] ?? '')
                                                      .toString();
                                                  final name =
                                                      (u['full_name'] ?? '')
                                                          .toString();
                                                  final company = u['company'];
                                                  String companyLabel = '';
                                                  if (company is Map) {
                                                    final cname =
                                                        (company['name'] ?? '')
                                                            .toString();
                                                    final slug =
                                                        (company['slug'] ?? '')
                                                            .toString();
                                                    companyLabel = cname
                                                            .isNotEmpty
                                                        ? (slug.isNotEmpty
                                                            ? '$cname ($slug)'
                                                            : cname)
                                                        : '';
                                                  }

                                                  return Card(
                                                    color: _selectedUserId == id
                                                        ? Colors.white
                                                            .withOpacity(0.09)
                                                        : Colors.white
                                                            .withOpacity(0.03),
                                                    shape:
                                                        RoundedRectangleBorder(
                                                      borderRadius:
                                                          BorderRadius.circular(
                                                              12),
                                                      side: BorderSide(
                                                        color: _selectedUserId ==
                                                                id
                                                            ? Colors.cyan
                                                            : Colors
                                                                .transparent,
                                                      ),
                                                    ),
                                                    child: RadioListTile<int>(
                                                      value: (id is int)
                                                          ? id
                                                          : int.tryParse(id
                                                                  .toString()) ??
                                                              -1,
                                                      groupValue:
                                                          _selectedUserId,
                                                      onChanged: (val) {
                                                        setState(() {
                                                          _selectedUserId = val;
                                                        });
                                                      },
                                                      title: Text(
                                                        role.isEmpty
                                                            ? 'User'
                                                            : role,
                                                        style: const TextStyle(
                                                            color:
                                                                Colors.white),
                                                      ),
                                                      subtitle: Text(
                                                        [name, companyLabel]
                                                            .where((s) =>
                                                                s.isNotEmpty)
                                                            .join(' • '),
                                                        style: const TextStyle(
                                                            color:
                                                                Colors.white70,
                                                            fontSize: 12),
                                                      ),
                                                    ),
                                                  );
                                                }).toList(),
                                                const SizedBox(height: 12),
                                                Row(
                                                  children: [
                                                    Expanded(
                                                      child: ElevatedButton(
                                                        onPressed:
                                                            _selectedUserId ==
                                                                    null
                                                                ? null
                                                                : _continueWithSelectedRole,
                                                        child: const Text(
                                                            'Continue'),
                                                      ),
                                                    ),
                                                    const SizedBox(width: 8),
                                                    TextButton(
                                                      onPressed: () {
                                                        setState(() {
                                                          _roleSelectionUsers =
                                                              null;
                                                          _selectedUserId =
                                                              null;
                                                          _generalError =
                                                              'Login cancelled.';
                                                        });
                                                      },
                                                      child:
                                                          const Text('Cancel'),
                                                    ),
                                                  ],
                                                ),
                                                const SizedBox(height: 12),
                                              ],
                                            ),
                                          ],
                                          if (_roleSelectionUsers == null) ...[
                                            const SizedBox(height: 12),

                                            // General error banner
                                            if (_generalError != null)
                                              Container(
                                                width: double.infinity,
                                                padding:
                                                    const EdgeInsets.symmetric(
                                                        vertical: 10,
                                                        horizontal: 12),
                                                margin: const EdgeInsets.only(
                                                    bottom: 12),
                                                decoration: BoxDecoration(
                                                  color: Colors.redAccent
                                                      .withOpacity(0.12),
                                                  borderRadius:
                                                      BorderRadius.circular(10),
                                                  border: Border.all(
                                                    color: Colors.redAccent
                                                        .withOpacity(0.2),
                                                  ),
                                                ),
                                                child: Text(
                                                  _generalError!,
                                                  style: const TextStyle(
                                                    color: Colors.redAccent,
                                                    fontWeight: FontWeight.w600,
                                                  ),
                                                ),
                                              ),

                                            const SizedBox(height: 10),

                                            TextFormField(
                                              controller: _emailController,
                                              keyboardType:
                                                  TextInputType.emailAddress,
                                              style: const TextStyle(
                                                  color: Colors.white),
                                              decoration: InputDecoration(
                                                filled: true,
                                                fillColor: Colors.white
                                                    .withOpacity(0.03),
                                                prefixIcon: const Icon(
                                                    Icons.email_outlined,
                                                    color: Colors.white70),
                                                labelText: 'Email',
                                                labelStyle: const TextStyle(
                                                    color: Colors.white70),
                                                hintText: 'you@email.com',
                                                hintStyle: const TextStyle(
                                                    color: Colors.white38),
                                                border: OutlineInputBorder(
                                                  borderRadius:
                                                      BorderRadius.circular(12),
                                                  borderSide: BorderSide.none,
                                                ),
                                                errorText: _emailError,
                                              ),
                                              validator: (v) {
                                                if (v == null ||
                                                    v.trim().isEmpty)
                                                  return 'Please enter your email';
                                                if (!RegExp(
                                                        r'^[^@]+@[^@]+\.[^@]+')
                                                    .hasMatch(v.trim()))
                                                  return 'Enter a valid email';
                                                return null;
                                              },
                                            ),

                                            const SizedBox(height: 16),

                                            TextFormField(
                                              controller: _passwordController,
                                              obscureText: _obscurePassword,
                                              style: const TextStyle(
                                                  color: Colors.white),
                                              decoration: InputDecoration(
                                                filled: true,
                                                fillColor: Colors.white
                                                    .withOpacity(0.03),
                                                prefixIcon: const Icon(
                                                    Icons.lock_outline,
                                                    color: Colors.white70),
                                                labelText: 'Password',
                                                labelStyle: const TextStyle(
                                                    color: Colors.white70),
                                                border: OutlineInputBorder(
                                                  borderRadius:
                                                      BorderRadius.circular(12),
                                                  borderSide: BorderSide.none,
                                                ),
                                                suffixIcon: IconButton(
                                                  onPressed: () {
                                                    setState(() {
                                                      _obscurePassword =
                                                          !_obscurePassword;
                                                    });
                                                  },
                                                  icon: Icon(
                                                    _obscurePassword
                                                        ? Icons
                                                            .visibility_outlined
                                                        : Icons
                                                            .visibility_off_outlined,
                                                    color: Colors.white70,
                                                  ),
                                                ),
                                                errorText: _passwordError,
                                              ),
                                              validator: (v) {
                                                if (v == null || v.isEmpty)
                                                  return 'Please enter your password';
                                                if (v.length < 6)
                                                  return 'Password must be at least 6 characters';
                                                return null;
                                              },
                                            ),

                                            const SizedBox(height: 12),

                                            // remember + forgot
                                            Row(
                                              children: [
                                                Checkbox(
                                                  value: _rememberMe,
                                                  onChanged: (val) {
                                                    setState(() {
                                                      _rememberMe =
                                                          val ?? false;
                                                    });
                                                  },
                                                  activeColor:
                                                      Color(0xFF5E35B1),
                                                ),
                                                const SizedBox(width: 6),
                                                GestureDetector(
                                                  onTap: () {
                                                    setState(() {
                                                      _rememberMe =
                                                          !_rememberMe;
                                                    });
                                                  },
                                                  child: const Text(
                                                      'Remember me',
                                                      style: TextStyle(
                                                          color:
                                                              Colors.white70)),
                                                ),
                                                const Spacer(),
                                                TextButton(
                                                  onPressed:
                                                      _showForgotPasswordDialog,
                                                  child: const Text(
                                                      'Forgot password?',
                                                      style: TextStyle(
                                                          color: Colors.white70,
                                                          fontWeight:
                                                              FontWeight.w600)),
                                                ),
                                              ],
                                            ),

                                            const SizedBox(height: 16),

                                            // Beautified sign-in button (removed sign-up row)
                                            _animatedSignInButton(
                                              onPressed: _handleLogin,
                                              loading: _loading,
                                            ),

                                            const SizedBox(height: 8),
                                          ],
                                        ]),
                                  ),
                                ),
                              ),
                            ),
                          ),
                        ),
                      ),

                      // Sign-up link (Client / Marketer) and Company registration button placed below the card to match web layout
                      const SizedBox(height: 12),
                      Center(
                        child: GestureDetector(
                          onTap: _showAccountTypeDialog,
                          child: RichText(
                            text: const TextSpan(
                              text: 'Create Client or Affiliate Account? ',
                              style: TextStyle(color: Colors.white70),
                              children: [
                                TextSpan(
                                  text: 'Sign up',
                                  style: TextStyle(
                                    color: Color(0xFF11998E),
                                    fontWeight: FontWeight.w700,
                                  ),
                                )
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 12),
                      Center(
                        child: ElevatedButton(
                          style: ElevatedButton.styleFrom(
                            backgroundColor: const Color(0xFF11998E),
                            padding: const EdgeInsets.symmetric(
                                vertical: 12, horizontal: 18),
                            shape: RoundedRectangleBorder(
                                borderRadius: BorderRadius.circular(12)),
                            elevation: 6,
                          ),
                          onPressed: _showCompanyRegistrationDialog,
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: const [
                              Icon(Icons.business, color: Colors.white),
                              SizedBox(width: 8),
                              Text('Register Your Company',
                                  style: TextStyle(
                                      color: Colors.white,
                                      fontWeight: FontWeight.w700)),
                            ],
                          ),
                        ),
                      ),

                      const SizedBox(height: 14),
                      Center(
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: const [
                            // Security badge
                            Padding(
                              padding: EdgeInsets.symmetric(
                                  horizontal: 6.0, vertical: 6.0),
                              child: Text('🔒 SSL 256-bit Encrypted',
                                  style: TextStyle(color: Colors.white70)),
                            ),
                            SizedBox(height: 4),
                            Text('© 2025 Lamba Real Estate Management',
                                style: TextStyle(
                                    color: Colors.white54, fontSize: 12)),
                          ],
                        ),
                      ),

                      const SizedBox(height: 22),
                    ],
                  ),
                ),
              );
            }),
          ),
        ],
      ),
    );
  }
}
