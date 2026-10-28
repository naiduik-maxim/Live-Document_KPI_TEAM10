// Independently compare test cases and assertions after moving React modules.
// Imports and mocks may change paths; behavioral expectations must remain.
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const ts = require('../../frontend/node_modules/typescript');

const root = path.resolve(__dirname, '../..');
const baseline = JSON.parse(fs.readFileSync(
  path.join(root, 'docs/verification/comments-ui-baseline.json'), 'utf8',
).replace(/^\uFEFF/, ''));
const current = new Map();
function collect(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const file = path.join(directory, entry.name);
    if (entry.isDirectory()) collect(file);
    else if (file.endsWith('.test.tsx')) current.set(entry.name, file);
  }
}
collect(path.join(root, 'frontend/src'));

function behavior(source) {
  const file = ts.createSourceFile('test.tsx', source, ts.ScriptTarget.Latest, true, ts.ScriptKind.TSX);
  const cases = [];
  const assertions = [];
  const printer = ts.createPrinter({ removeComments: true });
  function startsWithExpect(expression) {
    if (ts.isIdentifier(expression)) return expression.text === 'expect';
    if (ts.isPropertyAccessExpression(expression) || ts.isCallExpression(expression)) {
      return startsWithExpect(expression.expression);
    }
    return false;
  }
  function visit(node) {
    if (ts.isCallExpression(node)) {
      if (ts.isIdentifier(node.expression) && ['it', 'test'].includes(node.expression.text)) {
        cases.push(node.arguments[0].text);
      }
      // Capture the full matcher expression, including its expected argument.
      if (ts.isPropertyAccessExpression(node.expression)
          && startsWithExpect(node.expression)) {
        assertions.push(printer.printNode(ts.EmitHint.Unspecified, node, file));
      }
    }
    ts.forEachChild(node, visit);
  }
  visit(file);
  return { cases, assertions };
}

let totalCases = 0;
let totalAssertions = 0;
for (const [name, source] of Object.entries(baseline)) {
  assert(current.has(name), `Missing moved test file: ${name}`);
  const before = behavior(source);
  const after = behavior(fs.readFileSync(current.get(name), 'utf8'));
  // New regression cases may be appended; earlier expectations must survive.
  assert.deepEqual(after.cases.slice(0, before.cases.length), before.cases, `Cases changed in ${name}`);
  assert.deepEqual(after.assertions.slice(0, before.assertions.length), before.assertions, `Assertions changed in ${name}`);
  totalCases += before.cases.length;
  totalAssertions += before.assertions.length;
  console.log(`PASS ${path.relative(root, current.get(name))}: ${before.cases.length} original cases, ${before.assertions.length} original assertions unchanged`);
}
console.log(`PASS ${totalCases} cases, ${totalAssertions} assertions retained across ${Object.keys(baseline).length} files`);
