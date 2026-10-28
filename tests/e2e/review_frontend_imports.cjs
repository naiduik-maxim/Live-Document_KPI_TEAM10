// Read-only diagnostic for local module resolution and circular imports.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const ts = require('../../frontend/node_modules/typescript');
const root = path.resolve(__dirname, '../../frontend/src');
const files = [];
function collect(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(file);
    else if (/\.tsx?$/.test(file) && !file.endsWith('.test.tsx')) files.push(file);
  }
}
collect(root);
const graph = new Map();
for (const file of files) {
  const source = ts.createSourceFile(file, fs.readFileSync(file, 'utf8'), ts.ScriptTarget.Latest, true);
  const edges = [];
  for (const node of source.statements) {
    if (!(ts.isImportDeclaration(node) || ts.isExportDeclaration(node))) continue;
    const specifier = node.moduleSpecifier?.text;
    if (!specifier?.startsWith('.')) continue;
    const base = path.resolve(path.dirname(file), specifier);
    const target = [base, `${base}.ts`, `${base}.tsx`, path.join(base, 'index.ts'), path.join(base, 'index.tsx')]
      .find(candidate => fs.existsSync(candidate) && fs.statSync(candidate).isFile());
    assert(target, `Unresolved local import ${specifier} in ${file}`);
    if (/\.tsx?$/.test(target)) edges.push(target);
  }
  graph.set(file, edges);
}
const complete = new Set();
function visit(file, active = []) {
  assert(!active.includes(file), `Circular import: ${[...active, file].map(item => path.relative(root, item)).join(' -> ')}`);
  if (complete.has(file)) return;
  for (const target of graph.get(file) || []) visit(target, [...active, file]);
  complete.add(file);
}
for (const file of files) visit(file);
console.log(`PASS ${files.length} production/support TypeScript modules; local imports resolve; no cycles`);
const context = path.join(root, 'features/auth/context/SessionContext.tsx');
assert((graph.get(context) || []).every(file => !file.includes(`${path.sep}app${path.sep}`)));
console.log('PASS SessionContext has no dependency on app composition or route pages');
