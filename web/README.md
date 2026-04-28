# UniPush Web Console

前端控制台基于 React、Vite、Tailwind 和 shadcn/ui。

## 本地开发

```bash
npm install
npm run dev
```

默认开发地址：`http://localhost:5173`

## 质量检查

```bash
npm run lint
npm run build
```

## 页面结构

- `/login` 登录
- `/` 概览面板
- `/channels` 通道管理
- `/push-keys` 推送密钥
- `/messages` 消息记录
- `/messages/:id` 消息详情
- `/profile` 个人设置
- `/users` 用户管理（仅管理员）

## 设计约束

- 统一使用仓库内现有的 shadcn/ui 标准组件
- 保持现有表单、表格、卡片和对话框风格
- 业务页面不引入新的自定义 UI 组件体系
