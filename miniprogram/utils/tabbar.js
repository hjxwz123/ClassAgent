// 在 Tab 页 onShow 中调用，高亮当前 Tab 并同步角色
function setTab(page, index) {
  if (typeof page.getTabBar === 'function' && page.getTabBar()) {
    const bar = page.getTabBar();
    bar.refreshRole();
    if (bar.data.selected !== index) bar.setData({ selected: index });
  }
}

module.exports = { setTab };
