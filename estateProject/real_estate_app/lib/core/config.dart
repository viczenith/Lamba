class Config {
  static const String devBaseUrl = 'http://172.20.248.72:8000/api';
  static const String prodBaseUrl = 'https://lamba-backend.onrender.com/api';

  static String get baseUrl {
    return _useProductionBackend ? prodBaseUrl : devBaseUrl;
  }

  // Use the local dev backend for testing. Set to `false` to point to dev.
  // Toggle to route API calls to prod or dev at runtime. Set to false for local/dev testing.
  static bool _useProductionBackend = false;

  // Public accessor for other libraries to read the runtime flag (private field kept internal).
  static bool get useProductionBackend => _useProductionBackend;

  static const Map<String, String> defaultHeaders = {
    'Content-Type': 'application/json',
  };

  // API Endpoints //
  static const String loginEndpoint = '/api-token-auth/';
  static const String supportBirthdaySummary =
      '/admin-support/birthdays/summary/';
  static const String supportSpecialDayCounts =
      '/admin-support/special-days/counts/';
  static const String supportBirthdayCounts =
      '/admin-support/birthdays/counts/';
}
