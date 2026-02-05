# Backend Patterns

> Copy to your project's `docs/` and fill in project-specific patterns.

---

## Function Handler Pattern

```javascript
const appHttp = require("../../../shared/utils/appHttpWithLogging");
const { successResponse, errorResponse } = require("../../../shared/utils/responseHandler");
const db = require("../../../models");

appHttp("GetResource", {
  methods: ["GET"],
  authLevel: "anonymous",
  route: "bandar-admin/resources/{id}",
  handler: async (request, context) => {
    try {
      const resource = await db.Resource.findByPk(request.params.id);
      if (!resource) return errorResponse(404, "Resource not found");
      return successResponse(200, "Success", resource);
    } catch (error) {
      context.error(error);
      return errorResponse(500, error.message);
    }
  },
});
```

**Reference:** `src/functions/admin/auth/adminAuth.function.js`

---

## Validation Pattern

```javascript
// src/functions/admin/validations/resourceValidation.js
const { body, param } = require("express-validator");

const createValidation = [
  body("name").notEmpty().withMessage("Name required"),
  body("status").optional().isIn(["active", "inactive"]),
];
```

**Reference:** `src/functions/admin/validations/`

---

## Response Pattern

```javascript
// Success: { success: true, status: 200, message: "...", data: {...} }
return successResponse(200, "Created", resource);

// Error: { success: false, status: 400, message: "..." }
return errorResponse(400, "Invalid input");
```

---

## Model Pattern

```javascript
class Resource extends Model {
  static associate(models) {
    Resource.belongsTo(models.Category, { foreignKey: "categoryId", as: "category" });
  }
}

Resource.init({
  id: { type: DataTypes.UUID, defaultValue: DataTypes.UUIDV4, primaryKey: true },
  name: DataTypes.STRING,
  status: { type: DataTypes.ENUM("active", "inactive"), defaultValue: "active" },
}, { sequelize, modelName: "Resource", timestamps: true });
```

**Reference:** `src/models/admin.js`

---

## Migration Pattern

```javascript
module.exports = {
  async up(queryInterface, Sequelize) {
    await queryInterface.createTable("Resources", { /* columns */ });
    await queryInterface.addIndex("Resources", ["status"]);
  },
  async down(queryInterface) {
    await queryInterface.dropTable("Resources");
  },
};
```

---

## Project-Specific

> Fill in below:

- API Prefixes: `/bandar-admin/`, `/bandar-vendor/`, `/bandar-customer/`
- Common enums: `src/shared/constants/commanEnum.js`
- Email helper: `src/shared/utils/emailHandler.js`
