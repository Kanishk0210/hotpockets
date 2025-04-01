# @app.get("/api/revenue",

# @app.get("/api/get-rawmaterial-activity",


# Here's the documentation for the work we've done:

# # API Documentation

# ## 1. Revenue Tracking API
# Endpoint to fetch and aggregate revenue data based on branch, date range, and aggregation type.

# ### Endpoint
# ```
# GET /api/revenue
# ```

# ### Authentication
# - Requires JWT Bearer token
# - Branch information is extracted from the token

# ### Query Parameters
# | Parameter   | Type   | Required | Description                                    |
# |------------|--------|----------|------------------------------------------------|
# | branchCode | string | Yes      | Unique identifier for the branch               |
# | startTime  | string | Yes      | Start date/time (YYYY-MM-DD HH:mm:ss)         |
# | endTime    | string | Yes      | End date/time (YYYY-MM-DD HH:mm:ss)           |
# | retType    | string | Yes      | Aggregation type ('day' or 'month')           |

# ### Response Format
# ```json
# {
#   "totalCashCollec": 600,
#   "totalOnlineCollec": 1000,
#   "revenueDetails": [
#     {
#       "d": "YYYY-MM-DD or YYYY-MM",
#       "revenue": 50
#     }
#   ]
# }
# ```

# ### Response Fields
# | Field            | Type    | Description                                        |
# |------------------|---------|---------------------------------------------------|
# | totalCashCollec  | number  | Total revenue collected via cash payments         |
# | totalOnlineCollec| number  | Total revenue collected via online payments       |
# | revenueDetails   | array   | Array of date-wise or month-wise revenue details  |
# | d                | string  | Date (YYYY-MM-DD) or Month (YYYY-MM)             |
# | revenue          | number  | Total revenue for the period                      |

# ### Error Responses
# | Status Code | Description                                        |
# |-------------|----------------------------------------------------|
# | 400         | Invalid date format or retType                     |
# | 403         | Authentication error                               |
# | 500         | Server error                                       |

# ## 2. Raw Material Audit System
# System to track all changes made to raw materials inventory.

# ### Models

# #### RawMaterialAudit
# ```python
# class RawMaterialAudit(BaseModel):
#     Id: str = None
#     Type: str = constants.RAWMTRL_AUDIT
#     RawMaterialId: str
#     Action: str  # "ADD", "EDIT", "DELETE"
#     EmployeeId: str
#     CreatedAt: str
#     CreatedBy: str
#     PreviousValue: Optional[dict] = None
#     NewValue: Optional[dict] = None
#     Branch: str
# ```

# ### Database Structure
# - Branch-specific audit collections: `{branchCode}-masterdata-target-audit`
# - Maintains separate audit trails for each branch
# - Stores complete history of changes

# ### Logging Implementation
# ```python
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.StreamHandler(sys.stdout)
#     ]
# )
# ```

# ### Log Levels
# | Level   | Usage                                              |
# |---------|---------------------------------------------------|
# | INFO    | Successful operations, request details             |
# | WARNING | Skipped operations, non-critical issues           |
# | ERROR   | Failed operations, exceptions                     |

# ### Example Log Output
# ```
# 2024-03-20 10:15:30,123 - main - INFO - Received revenue request - Branch: BR001
# 2024-03-20 10:15:30,234 - main - INFO - Fetching bills from database...
# 2024-03-20 10:15:30,345 - database.firebase_conn - INFO - Found 150 bills
# ```

# ## 3. Security Features
# - JWT-based authentication
# - Branch-level data isolation
# - Request validation
# - Error handling and logging

# ## 4. Best Practices Implemented
# 1. **Input Validation**
#    - Date format validation
#    - Parameter type checking
#    - Required field validation

# 2. **Error Handling**
#    - Structured error responses
#    - Detailed error logging
#    - Exception catching

# 3. **Performance**
#    - Efficient data aggregation
#    - Query optimization
#    - Response formatting

# 4. **Security**
#    - Authentication checks
#    - Branch data isolation
#    - Input sanitization

# ## 5. Usage Examples

# ### Fetch Daily Revenue
# ```http
# GET /api/revenue?branchCode=BR001&startTime=2024-03-01 00:00:00&endTime=2024-03-31 23:59:59&retType=day
# ```

# ### Fetch Monthly Revenue
# ```http
# GET /api/revenue?branchCode=BR001&startTime=2024-01-01 00:00:00&endTime=2024-12-31 23:59:59&retType=month
# ```

# This documentation covers the implementation of the revenue tracking system and raw material audit system, including API endpoints, data models, security features, and logging mechanisms.
