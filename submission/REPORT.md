# Báo cáo cá nhân — K4-L3B Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyễn Văn Đại
- **MSSV:** 2A202602477
- **Lớp:** K4-L3B
- **Repository URL:** https://github.com/NguyenVanDaidzvcc/K4-L3B-Day13-NguyenVanDai-2A202602477-Monitoring-LLMOps
- **Commit SHA cuối:** 2cefe0bfb5f04161e80520613dd3681767294873
- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** day13-k4-l3b-2A202602477

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.png` |
| Log validator | `evidence/02-log-validator.png` |
| Dashboard validator | `evidence/03-dashboard-validator.png` |
| Structured log | `evidence/04-structured-log.png` |
| PII redaction | `evidence/05-pii-redaction.png` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08a-trace-metadata.png`, `evidence/08b-generation.png` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10a-promote.png`, `evidence/10b-rollback.png` |
| Dashboard runtime | `evidence/11a-dashboard-latency-traffic.png`, `evidence/11b-dashboard-errors-cost.png`, `evidence/11c-dashboard-tokens-quality.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | Chưa lưu kết quả baseline | 100/100; 152 records, 75 correlation IDs, 0 PII leak | Chạy lại ngày 2026-09-30 |
| `validate_dashboard.py` | Chưa lưu kết quả baseline | HỢP LỆ: 6/6 panel | Contract hợp lệ |
| `pytest` | Chưa lưu kết quả baseline | 24 passed | Có cảnh báo pytest-asyncio về fixture loop scope |
| Số traces hợp lệ | Chưa ghi nhận | Chưa xác minh số trace trong Langfuse | Không suy ra từ số correlation ID trong log |
| Số PII leak | Chưa lưu kết quả baseline | 0 | Theo log validator |
| Latency P95 / TTFT P95 | Chưa lưu kết quả baseline | 5,153 ms / 50 ms | Ảnh dashboard trong cửa sổ incident |
| Retrieval success rate | Chưa lưu kết quả baseline | 100% | Ảnh dashboard trong cửa sổ incident |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware nhận `x-request-id` nếu client gửi; nếu không, sinh `req-<8 ký tự hex>`. ID được bind vào structlog context, gắn vào request state và trả lại trong response header `x-request-id`.
- **Các metadata được ghi vào structured log:** Timestamp UTC, event, service, level, correlation ID, environment, session, feature, model, user ID đã hash và các trường metric theo event như latency, TTFT, tokens, cost, quality.
- **Cách bảo đảm PII được scrub trước khi ghi:** Processor scrub chuỗi trong payload trước khi JSONL processor ghi file; user ID được hash trước khi log.
- **Cách kiểm chứng kết quả:** `python scripts/validate_logs.py` đạt 100/100 trên 152 records, 75 correlation IDs và 0 PII leak; xem `evidence/02-log-validator.png`, `evidence/04-structured-log.png`, `evidence/05-pii-redaction.png`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Đối chiếu project name và trace list trong `evidence/06-trace-list.png`; điền tên project đã xác nhận từ Langfuse ở mục 1.
- **Cấu trúc root/retrieval/generation observations:** `day13-agent-request` / `lab-agent-run` chứa child observations `retrieval` và `generation`; xem `evidence/07-trace-waterfall.png`.
- **Cách nối trace với log:** Metadata trace có `correlation_id`; đối chiếu `req-677db264` trong `evidence/13-incident-log.png` với `evidence/14-incident-trace.png`.
- **Prompt name:** Xác nhận tên prompt trong ảnh Langfuse `evidence/08a-trace-metadata.png` và `evidence/09-prompt-versions.png`.
- **Version/label baseline:** [điền theo Langfuse]
- **Version/label candidate:** [điền theo Langfuse]
- **Trace ID của mỗi version:** [điền các trace ID từ Langfuse]
- **Cách promote và rollback `production`:** Evidence promote/rollback nằm tại `evidence/10a-promote.png` và `evidence/10b-rollback.png`; mô tả version/label và trace ID thực tế sau khi xác nhận.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Streamlit đọc `data/logs.jsonl`; sáu panel gồm latency/TTFT, request traffic, error rate/retrieval success, cost, input/output tokens và quality score. Validator đạt 6/6. Ảnh: `evidence/11a-dashboard-latency-traffic.png`, `evidence/11b-dashboard-errors-cost.png`, `evidence/11c-dashboard-tokens-quality.png`.
- **SLO và lý do chọn:** `fast_successful_requests` đặt mục tiêu 99.5% trong 28 ngày; request tốt là `response_sent` có `latency_ms <= 3000`. Ngưỡng 3 giây cần được đối chiếu với baseline thực tế trước khi chốt.
- **Cách tính error budget:** 100% - 99.5% = 0.5%; tương đương tối đa 50 request không đạt trên 10,000 request trong cửa sổ SLO.
- **Ba alert và runbook tương ứng:** Chưa hoàn thiện; `config/alert_rules.yaml` hiện còn các trường TODO. Cần cấu hình trước khi báo cáo là đã triển khai.

> Ví dụ cách viết error budget: "SLO 99.5% trong 28 ngày nghĩa là error budget 0.5%. Nếu workload có 10,000 request thì tối đa 50 request được phép lỗi hoặc chậm hơn ngưỡng SLO."

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3b-monitoring-llmops-v1`; incident `rag_slow`, seed `1312`, ngưỡng challenge `2000 ms`.
- **Khoảng thời gian điều tra:** Request `req-677db264` từ `2026-09-30T08:30:10.376601Z` đến `2026-09-30T08:30:15.541920Z`.
- **Triệu chứng từ metrics:** Ảnh dashboard ghi latency P95 `5,153 ms`, cao hơn ngưỡng challenge `2,000 ms` và SLO `3,000 ms`; TTFT P95 `50 ms`, retrieval success `100%`. Xem `evidence/12-incident-metric.png`.
- **Log line và correlation ID liên quan:** `req-677db264`, session `k4-l3b-challenge-s01`, feature `monitoring`; `response_sent` ghi `latency_ms=5155`, `ttft_ms=50`, `tool_name=retrieval`, `tool_success=true`. Xem `evidence/13-incident-log.png`.
- **Trace ID và span gây ảnh hưởng:** Correlation ID `req-677db264`; span `retrieval` theo trace screenshot `evidence/14-incident-trace.png`. [Bổ sung trace ID hiển thị trong Langfuse.]
- **Root cause:** Challenge bật incident `rag_slow`; `app/mock_rag.py` chèn độ trễ 2.5 giây vào thao tác retrieval. Request có latency xấp xỉ 5.15 giây. Trong `app/agent.py`, retrieval hiện được gọi trước và sau khi mở child observation; cần xác nhận trace span và rà soát lần gọi lặp này khi diễn giải latency.
- **Fix action:** Sau khi chụp evidence, tắt incident bằng `python scripts/inject_incident.py --disable` và xác nhận `/health` báo incident `rag_slow: false`. Chưa ghi nhận việc khôi phục đã hoàn tất.
- **Preventive measure:** Hoàn thiện alert P95 theo SLO/challenge và regression test cho latency retrieval; hiện `config/alert_rules.yaml` vẫn còn TODO.

> Gợi ý cách viết ngắn, không thay cho evidence thực tế: "Metric cho thấy `[latency/error/cost/quality]` bất thường trong `[khoảng thời gian]`. Log line `[event]` có `correlation_id=[...]` đại diện cho request bị ảnh hưởng. Trace cùng `correlation_id` cho thấy span `[retrieval/generation/prompt/tool]` có dấu hiệu `[chậm/lỗi/token tăng]`. Root cause là `[nguyên nhân suy ra từ evidence]`. Fix action là `[hành động khôi phục]`; preventive measure là `[alert/runbook/test/guardrail để ngăn tái diễn]`."

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Dashboard local dùng Streamlit và `data/logs.jsonl`, theo contract `config/dashboard.yaml`, để xem dữ liệu runtime mà không cần dựng thêm dịch vụ metrics.
- **Một lỗi/blocker đã gặp:** Load test ban đầu báo `WinError 10061` khi API không nhận kết nối; đồng thời PowerShell ghép câu lệnh kế tiếp vào lệnh `load_test.py`.
- **Cách tìm nguyên nhân và xử lý:** Xác nhận API chạy riêng ở cổng 8000, bật incident trước workload challenge, rồi chạy lại `python scripts/load_test.py --challenge --concurrency 5`.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metric phát hiện P95 tăng; log xác định request `req-677db264`; trace cùng correlation ID khoanh vùng retrieval.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** [bổ sung nhận xét cá nhân sau khi đối chiếu evidence prompt và rollback]
- **Điều quan trọng nhất đã học:** [bổ sung bằng lời của bạn]
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** `config/alert_rules.yaml` còn TODO; repository URL, commit SHA, tên project/trace ID và các chi tiết prompt version cần xác nhận trước khi nộp.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [ ] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [ ] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [ ] Repository chạy lại được theo README.
- [ ] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
