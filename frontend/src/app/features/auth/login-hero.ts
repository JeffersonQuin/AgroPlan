import { Component } from '@angular/core';

/**
 * Marketing panel of the authentication screen: brand pill, value proposition,
 * metric badges and a testimonial, over the topographic contour background.
 */
@Component({
  selector: 'app-login-hero',
  templateUrl: './login-hero.html',
  host: {
    class:
      'relative w-full lg:w-5/12 bg-primary p-space-xl lg:p-margin-desktop text-on-primary flex flex-col justify-between overflow-hidden min-h-[420px] lg:min-h-[640px]',
  },
})
export class LoginHero {}
