import { createRequire } from 'node:module';
import { dirname, join } from 'node:path';

export const name = 'blender-mentor';
export const PACKAGE_NAME = 'blender-mentor';

export function resolveBlenderMentorSkillRoot(profileBaseUrl) {
  if (!profileBaseUrl) {
    throw new Error('blender-mentor: missing DSH profile baseUrl for package resolution');
  }
  const manifestPath = createRequire(profileBaseUrl).resolve(`${PACKAGE_NAME}/package.json`);
  return join(dirname(manifestPath), 'skills');
}
