
/* ===== 数字滚动 ===== */
function animateCount(el){
  const target = parseFloat(el.getAttribute('data-count'));
  const dur = 1400, start = performance.now();
  function tick(now){
    const p = Math.min((now - start) / dur, 1);
    const eased = 1 - Math.pow(1 - p, 3);
    const val = Math.round(target * eased);
    el.textContent = val.toLocaleString('en-US');
    if(p < 1) requestAnimationFrame(tick);
    else el.textContent = target.toLocaleString('en-US');
  }
  requestAnimationFrame(tick);
}

/* ===== 滚动进入 + 数字触发 ===== */
const io = new IntersectionObserver((entries)=>{
  entries.forEach(e=>{
    if(e.isIntersecting){
      e.target.classList.add('in');
      e.target.querySelectorAll('.num[data-count]').forEach(animateCount);
      io.unobserve(e.target);
    }
  });
},{threshold:.08});

document.querySelectorAll('.reveal').forEach(el=>io.observe(el));
document.querySelectorAll('.hstat, .metric-card').forEach(el=>io.observe(el));

/* 兜底：已进入视口但 IO 未及时触发的元素，立即置为可见 */
(function(){const vh=window.innerHeight;document.querySelectorAll('.reveal').forEach(el=>{
  if(el.getBoundingClientRect().top < vh*0.92) el.classList.add('in');
});})();

/* ===== 产品演示 Tab 切换 ===== */
const tabs = document.querySelectorAll('.demo-tab');
const panels = document.querySelectorAll('.demo-panel');
tabs.forEach(t=>{
  t.addEventListener('click',()=>{
    tabs.forEach(x=>x.classList.remove('on'));
    t.classList.add('on');
    panels.forEach(p=>p.classList.remove('on'));
    const target = document.getElementById(t.getAttribute('data-panel'));
    if(target) target.classList.add('on');
  });
});

/* ===== 趋势图（SVG 手绘） ===== */
/* 趋势图由下方注入脚本的数据驱动 drawTrendGrid 渲染 */
