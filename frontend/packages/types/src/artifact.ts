export interface PortalArtifact {
  children?: string;
  id: string;
  identifier?: string;
  language?: string;
  title?: string;
  type?: string;
}

export enum ArtifactType {
  Code = 'application/foxmask.artifacts.code',
  Default = 'html',
  Python = 'python',
  React = 'application/foxmask.artifacts.react',
}
