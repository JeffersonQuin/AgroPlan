import { Component, computed, input, output } from '@angular/core';
import { NgIcon, provideIcons } from '@ng-icons/core';
import {
  matArrowForwardOutline,
  matCheckCircleOutline,
  matContentCopyOutline,
  matDeleteOutline,
  matEditNoteOutline,
  matEditOutline,
  matEcoOutline,
  matMoreVertOutline,
  matPendingOutline,
  matSettingsOutline,
  matStraightenOutline,
  matTuneOutline,
  matVerifiedOutline,
  matWaterDropOutline,
} from '@ng-icons/material-symbols/outline';
import { Project, ProjectCardIcon } from '../../models/project.model';
import { formatArea, formatModifiedAt } from '../../utils/project-format';
import { ProjectPreview } from '../project-preview/project-preview';

/**
 * The registry name of the icon each `ProjectCardIcon` key renders.
 *
 * `provideIcons({ matVerifiedOutline })` registers that name as the key and the SVG as the
 * value, so the name `[name]` receives must be the string, never the SVG constant.
 */
const CARD_ICONS: Record<ProjectCardIcon, string> = {
  verified: 'matVerifiedOutline',
  pending: 'matPendingOutline',
  check_circle: 'matCheckCircleOutline',
  edit_note: 'matEditNoteOutline',
  tune: 'matTuneOutline',
  settings: 'matSettingsOutline',
};

/** One project in the dashboard grid, with its schematic and key metrics. */
@Component({
  selector: 'app-project-card',
  imports: [ProjectPreview, NgIcon],
  viewProviders: [
    provideIcons({
      matArrowForwardOutline,
      matCheckCircleOutline,
      matContentCopyOutline,
      matDeleteOutline,
      matEditNoteOutline,
      matEditOutline,
      matEcoOutline,
      matMoreVertOutline,
      matPendingOutline,
      matSettingsOutline,
      matStraightenOutline,
      matTuneOutline,
      matVerifiedOutline,
      matWaterDropOutline,
    }),
  ],
  templateUrl: './project-card.html',
})
export class ProjectCard {
  readonly project = input.required<Project>();

  readonly open = output<Project>();

  /** Resolves a dynamic icon key to the constant declared in `provideIcons`. */
  protected iconName(icon: ProjectCardIcon): string {
    return CARD_ICONS[icon];
  }

  protected readonly areaLabel = computed(() =>
    formatArea(this.project().areaM2, this.project().unitSystem),
  );

  protected readonly modifiedLabel = computed(() => formatModifiedAt(this.project().modifiedAt));
}
