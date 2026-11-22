import { Component } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matAgricultureOutline,
  matPolylineOutline,
  matSchemaFillOutline,
  matWaterDropOutline,
} from '@ng-icons/material-symbols/outline';

/**
 * Marketing panel of the authentication screen: brand pill, value proposition,
 * metric badges and a testimonial, over the topographic contour background.
 */
@Component({
  selector: 'app-login-hero',
  imports: [NgIcon],
  templateUrl: './login-hero.html',
  viewProviders: [
    provideIcons({
      matAgricultureOutline,
      matPolylineOutline,
      matSchemaFillOutline,
      matWaterDropOutline,
    }),
  ],
  host: {
    class:
      'relative hidden lg:flex lg:w-5/12 bg-primary p-space-xl lg:p-margin-desktop text-on-primary flex-col justify-between overflow-hidden lg:min-h-[640px]',
  },
})
export class LoginHero {}
