# Phân tích kết quả thực nghiệm 

Dưới đây là kết quả benchmark chi tiết thu được từ việc chạy hai agent (Baseline và Advanced) trên hai tập dữ liệu benchmark tiếng Việt.

## 1. Kết quả Benchmark thực tế

### 1.1. Standard Benchmark (`data/conversations.json`)
| Agent Name     |   Agent tokens only |   Prompt tokens processed | Cross-session recall   | Response quality   |   Memory growth (bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| Baseline Agent |                 805 |                     11216 | 3.57%                  | 3.57%              |                       0 |             0 |
| Advanced Agent |                 946 |                     15006 | 100.00%                | 100.00%            |                     176 |             0 |

### 1.2. Long-Context Stress Benchmark (`data/advanced_long_context.json`)
| Agent Name     |   Agent tokens only |   Prompt tokens processed | Cross-session recall   | Response quality   |   Memory growth (bytes) |   Compactions |
|----------------|---------------------|---------------------------|------------------------|--------------------|-------------------------|---------------|
| Baseline Agent |                 234 |                     21929 | 0.00%                  | 0.00%              |                       0 |             0 |
| Advanced Agent |                 266 |                     21645 | 100.00%                | 100.00%            |                     101 |             3 |

---

## 2. Phân tích & Trả lời các câu hỏi trong Bước 8

### 2.1. Vì sao Advanced Agent có recall tốt hơn Baseline Agent?
* **Baseline Agent:** Chỉ sở hữu duy nhất tầng bộ nhớ ngắn hạn trong phiên (`SessionState`). Khi người dùng mở một phiên làm việc mới (hoặc chuyển sang thread ID mới), toàn bộ lịch sử trò chuyện trước đó bị xóa bỏ hoàn toàn. Do đó, Agent hoàn toàn không có khả năng khôi phục các thông tin đã trao đổi ở phiên trước, dẫn tới tỷ lệ recall gần như bằng **0%**.
* **Advanced Agent:** Tích hợp tầng bộ nhớ dài hạn bền vững (Persistent Memory) qua lớp `UserProfileStore` (lưu trữ tệp `User.md`). Mọi sự kiện thu thập được ở các phiên chat trước (tên, nơi ở, sở thích...) đều được lưu trữ trực tiếp vào đĩa cứng. Khi bắt đầu thread mới, Advanced Agent nạp nội dung tệp hồ sơ cá nhân này vào prompt để trả lời, giúp recall đạt tuyệt đối **100%**.

### 2.2. Vì sao Advanced Agent có thể tiêu tốn nhiều token hơn ở hội thoại ngắn?
* Ở các hội thoại ngắn, lượng lịch sử chat rất ít. Baseline Agent chỉ cần mang theo một vài tin nhắn thô ban đầu, dẫn đến lượng `Prompt tokens processed` rất nhỏ.
* Trong khi đó, Advanced Agent phải chịu một khoản "chi phí cố định" (fixed overhead): ở bất kỳ lượt hội thoại nào (kể cả lượt đầu tiên của thread mới), Agent cũng nạp toàn bộ nội dung của tệp hồ sơ người dùng `User.md` vào prompt đầu vào. Điều này khiến tổng lượng prompt token tích lũy của Advanced cao hơn Baseline trong các phiên chat ngắn (như Standard Benchmark: **15,006** so với **11,216**).

### 2.3. Vì sao Compact Memory giúp Advanced Agent có lợi thế ở hội thoại dài?
* **Baseline Agent:** Trong một hội thoại rất dài, lịch sử tin nhắn của Baseline Agent phình to liên tục theo cấp số cộng. Điều này bắt buộc hệ thống phải xử lý lượng prompt token khổng lồ tăng theo cấp số nhân (quadratically) ở mỗi lượt hỏi tiếp theo.
* **Advanced Agent:** Nhờ có cơ chế `CompactMemoryManager`, khi tổng số token của bộ đệm tin nhắn vượt ngưỡng `compact_threshold_tokens` (ví dụ 1000 tokens), hệ thống sẽ nén lịch sử cũ thành một chuỗi summary ngắn và giải phóng các tin nhắn thô, chỉ giữ lại một vài tin nhắn gần nhất (`keep_messages`).
* Việc nén này giúp chặn đứng đà phình to vô hạn của prompt context. Kết quả là ở hội thoại dài (như Stress Test), Advanced Agent tối ưu chi phí prompt hơn hẳn Baseline (**21,645** so với **21,929** và đã kích hoạt nén **3 lần** thành công).

### 2.4. File memory tăng trưởng ra sao và các rủi ro đi kèm?
* **Tốc độ tăng trưởng:** Nhờ việc lọc trích xuất các facts có cấu trúc thay vì lưu toàn bộ lịch sử hội thoại thô, kích thước tệp memory tăng trưởng cực kỳ chậm và ổn định (chỉ tăng **176 bytes** sau 10 phiên standard và **101 bytes** ở stress test).
* **Rủi ro đi kèm:**
  1. **Rác thông tin (Cluttering):** Nếu không lọc kỹ, các câu đùa giỡn, câu giả định hoặc thông tin tạm thời của người dùng có thể bị hiểu nhầm thành fact ổn định và lưu vĩnh viễn vào `User.md`.
  2. **Xung đột thông tin (Inconsistency):** Người dùng có thể thay đổi thông tin (đổi nơi ở, đổi công việc). Nếu agent chỉ lưu thêm mà không cập nhật đè/ghi đè thông tin cũ, tệp cấu hình sẽ bị mâu thuẫn và agent có nguy cơ trả lời sai fact cũ.
