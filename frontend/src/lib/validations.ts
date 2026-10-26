import { z } from "zod";
import { VerificationCreate } from "@/types/api";

const bounded = (limit: number) => z.string().trim().refine(value => Array.from(value).length <= limit, `Tối đa ${limit} ký tự.`);
export const verificationFormSchema = z.object({
  company_name: bounded(255), tax_id: bounded(14), contact_email: bounded(255),
  recruitment_website: bounded(2048), social_channel_url: bounded(2048),
  account_number: bounded(50), bank_name: bounded(100), account_holder: bounded(255),
}).superRefine((values, ctx) => {
  if (!Object.values(values).some(Boolean)) ctx.addIssue({ code: "custom", path: [], message: "Hãy nhập ít nhất một thông tin để đối chiếu." });
  const bank = [values.account_number, values.bank_name, values.account_holder];
  if (bank.some(Boolean) && !bank.every(Boolean)) ctx.addIssue({ code: "custom", path: ["account_number"], message: "Cần nhập đủ ngân hàng, số tài khoản và chủ tài khoản." });
  if (values.tax_id && !/^[0-9]{10}(?:-?[0-9]{3})?$/.test(values.tax_id)) ctx.addIssue({ code: "custom", path: ["tax_id"], message: "Mã số thuế phải có 10 hoặc 13 chữ số." });
  if (values.contact_email && !z.email().safeParse(values.contact_email).success) ctx.addIssue({ code: "custom", path: ["contact_email"], message: "Email không đúng định dạng." });
  for (const field of ["recruitment_website", "social_channel_url"] as const) {
    if (!values[field]) continue;
    try {
      const url = new URL(values[field]);
      if (!["http:", "https:"].includes(url.protocol) || url.username || url.password) throw new Error();
    } catch {
      ctx.addIssue({ code: "custom", path: [field], message: "Hãy nhập URL HTTP hoặc HTTPS hợp lệ." });
    }
  }
});

export type VerificationFormValues = z.infer<typeof verificationFormSchema>;

export function verificationPayload(values: VerificationFormValues): VerificationCreate {
  const { account_number, bank_name, account_holder, ...fields } = values;
  return {
    ...Object.fromEntries(Object.entries(fields).filter(([, value]) => value !== "")),
    ...(account_number ? { bank_account: { account_number, bank_name, account_holder } } : {}),
  };
}
