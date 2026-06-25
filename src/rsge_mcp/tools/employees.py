"""Employee registry tools (eAPI ``Employees/*``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from ._common import compact

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from ..context import AppContext


def register(mcp: FastMCP, ctx: AppContext) -> None:
    @mcp.tool()
    async def rsge_get_countries(filters: dict[str, Any] | None = None) -> Any:
        """List countries (reference data for foreign employees).

        `filters` (optional): COUNTRY_NAME, COUNTRY_ID. Omit for all.
        """
        return await ctx.rest.post("/Employees/GetCountries", filters or {})

    @mcp.tool()
    async def rsge_get_employee(employee_id: int) -> Any:
        """Fetch a single registered employee by numeric id."""
        return await ctx.rest.post("/Employees/GetEmployee", {"ID": employee_id})

    @mcp.tool()
    async def rsge_list_employees(filters: dict[str, Any] | None = None) -> Any:
        """List registered employees with optional filters.

        `filters` (all optional): TIN, FULLNAME, STATUS (1=active / 0=terminated /
        -1=suspended), GENDER, WORK_TYPE, CITIZENSHIP, MAXIMUM_ROWS, and date ranges
        ('DD-MM-YYYY:DD-MM-YYYY') for BIRTH_DATE / CREATE_DATE / ACTIVATE_DATE /
        CANCEL_DATE / SUSPEND_DATE. Omit for the API defaults.
        """
        return await ctx.rest.post("/Employees/ListEmployees", filters or {})

    @mcp.tool()
    async def rsge_save_employee(
        tin: str,
        phone: str,
        work_type: int,
        is_foreigner: int = 0,
        employee_id: int = 0,
        fullname: str | None = None,
        gender: int | None = None,
        birth_date: str | None = None,
        citizen_country_id: str | None = None,
        status: int | None = None,
        extra: dict[str, Any] | None = None,
    ) -> Any:
        """Register (employee_id=0) or update (>0) an employee. WRITE — not auto-retried.

        - `work_type`: 1=full-time, 2=part-time.
        - `is_foreigner`: 0=Georgian (TIN is the personal id), 1=foreign — then `fullname`,
          `gender` (1=male / 2=female), `birth_date` ('DD-MM-YYYY') and `citizen_country_id`
          (see rsge_get_countries) are required.
        - `status`: 1=active, 0=terminated, -1=suspended.
        """
        employee = compact(
            {
                "ID": employee_id,
                "IS_FOREIGNER": is_foreigner,
                "TIN": tin,
                "PHONE": phone,
                "WORK_TYPE": work_type,
                "FULLNAME": fullname,
                "GENDER": gender,
                "BIRTH_DATE": birth_date,
                "CITIZEN_COUNTRY_ID": citizen_country_id,
                "STATUS": status,
            }
        )
        if extra:
            employee.update(extra)
        return await ctx.rest.post(
            "/Employees/SaveEmployee", employee, retry_reads=False, write=True
        )
