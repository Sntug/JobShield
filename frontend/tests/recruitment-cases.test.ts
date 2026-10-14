import { expect, test } from "vitest";
import canonicalCases from "../../backend/tests/fixtures/recruitment_cases.json";
import { recruitmentCases } from "./fixtures/recruitment-cases";

test("G2: frontend dùng cùng tình huống sản phẩm với backend", () => {
  expect(recruitmentCases).toEqual(canonicalCases.cases);
  const missing = recruitmentCases.find((item) => item.id === "missing_information");
  expect(missing?.expected.risk_label_vi).toBe("Không đủ thông tin");
  expect(missing?.expected.job?.company_name).toBeNull();
});
