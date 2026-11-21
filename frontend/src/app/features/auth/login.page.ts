import { Component } from '@angular/core';
import { LoginHero } from './login-hero';
import { LoginPanel } from './login-panel';

/**
 * Authentication screen: split layout with the brand hero on the left and the
 * credential form on the right, stacked on small viewports.
 */
@Component({
  selector: 'app-login-page',
  imports: [LoginHero, LoginPanel],
  templateUrl: './login.page.html',
})
export class LoginPage {}
