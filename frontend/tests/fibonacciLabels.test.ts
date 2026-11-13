import {test} from 'node:test';
import assert from 'node:assert/strict';
import {visibleFibonacciLabels} from '../src/fibonacciLabels.ts';
test('compressed Fibonacci levels keep endpoint labels and readable spacing',()=>{const levels=[0,.236,.382,.5,.618,.786,1].map(level=>({level,y:100-level*50}));const visible=visibleFibonacciLabels(levels);assert(visible.has(0)&&visible.has(1));const ys=levels.filter(p=>visible.has(p.level)).map(p=>p.y).sort((a,b)=>a-b);assert(ys.every((y,i)=>!i||y-ys[i-1]>=12));assert(visible.size<levels.length);});
test('expanded and reversed ratios stay visible; almost coincident levels show one label',()=>{const levels=[0,.236,.382,.5,.618,.786,1].map(level=>({level,y:level*200}));assert.equal(visibleFibonacciLabels(levels).size,7);assert.equal(visibleFibonacciLabels([{level:0,y:10},{level:1,y:15}]).size,1);});
