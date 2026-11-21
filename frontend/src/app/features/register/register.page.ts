import { Component } from '@angular/core';
import { RegisterForm } from './components/register-form/register-form';
import { RegisterHero } from './components/register-hero/register-hero';

/**
 * Sign-up screen: split layout with the capability hero on the left and the
 * registration form on the right, stacked on small viewports.
 */
@Component({
  selector: 'app-register-page',
  imports: [RegisterHero, RegisterForm],
  templateUrl: './register.page.html',
})
export class RegisterPage {}
