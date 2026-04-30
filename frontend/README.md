# ClassAgent Frontend

Vue3 前端，按 `UI.md` 设计规范实现。

## 启动

```bash
npm install
npm run dev -- --port 5173
```

默认代理：

- `/api` -> `http://127.0.0.1:8000`
- `/static` -> `http://127.0.0.1:8000`

## 构建

```bash
npm run build
```

## 线上 API 地址

可通过环境变量指定：

```env
VITE_API_BASE_URL=https://your-domain.example.com/api/v1
```
