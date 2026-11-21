import { Component, computed, input, output } from '@angular/core';
import { Project } from '../../models/project.model';
import { formatArea, formatModifiedAt } from '../../utils/project-format';
import { ProjectPreview } from '../project-preview/project-preview';

/** One project in the dashboard grid, with its schematic and key metrics. */
@Component({
  selector: 'app-project-card',
  imports: [ProjectPreview],
  templateUrl: './project-card.html',
})
export class ProjectCard {
  readonly project = input.required<Project>();

  readonly open = output<Project>();

  protected readonly areaLabel = computed(() =>
    formatArea(this.project().areaM2, this.project().unitSystem),
  );

  protected readonly modifiedLabel = computed(() => formatModifiedAt(this.project().modifiedAt));
}
