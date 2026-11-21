/**
 * Runtime configuration.
 *
 * `googleClientId` must be the same value the backend has in GOOGLE_CLIENT_ID,
 * and the origin (http://localhost:4200) must be authorised in Google Cloud
 * Console. While it stays empty the login screen shows a configuration notice
 * instead of a broken button.
 */
export const environment = {
  apiUrl: 'http://localhost:8000',
  googleClientId: '',
} as const;
