use vcpu::{get_hour_boundaries, timestamp_format, PrometheusClient};

#[tokio::test]
async fn query_against_mock_prometheus() {
    // Start a minimal mock server inline
    let listener = tokio::net::TcpListener::bind("127.0.0.1:0").await.unwrap();
    let addr = listener.local_addr().unwrap();

    tokio::spawn(async move {
        loop {
            let (mut stream, _) = listener.accept().await.unwrap();
            tokio::spawn(async move {
                use tokio::io::{AsyncReadExt, AsyncWriteExt};
                let mut buf = [0u8; 4096];
                let n = stream.read(&mut buf).await.unwrap_or(0);
                let req = String::from_utf8_lossy(&buf[..n]);
                let body = if req.contains("/api/v1/query_range") {
                    r#"{"status":"success","data":{"result":[{"metric":{},"values":[[1705323600,"16"],[1705323900,"18"]]}]}}"#
                } else if req.contains("empty") {
                    r#"{"status":"success","data":{"result":[]}}"#
                } else {
                    r#"{"status":"success","data":{"result":[{"metric":{},"value":[1705323600,"24"]}]}}"#
                };
                let resp = format!(
                    "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: {}\r\n\r\n{}",
                    body.len(),
                    body
                );
                let _ = stream.write_all(resp.as_bytes()).await;
            });
        }
    });

    let url = format!("http://{}", addr);
    let client = PrometheusClient::new(&url);

    // instant query returns value
    let val = client
        .get_current_value("max_over_time(sum(machine_cpu_cores)[59m59s999ms:5m] @ 1705323600.0)")
        .await
        .unwrap();
    assert_eq!(val, Some(24.0));

    // range query returns timeline
    let data = client
        .query_range("sum(machine_cpu_cores)", 1705323600.0, 1705327200.0, "5m")
        .await
        .unwrap();
    assert_eq!(data["status"], "success");
}

#[test]
fn hour_boundaries_parity_with_python() {
    // Python: (ts // 3600)*3600 - 3600, -0.001
    // Tested against Python's implementation for several values
    let cases = [
        (1705327200.0, (1705323600.0, 1705327199.999)),
        (0.0, (-3600.0, -0.001)),
        (3600.0, (0.0, 3599.999)),
    ];
    for (input, expected) in cases {
        assert_eq!(get_hour_boundaries(input), expected, "input={input}");
    }
}

#[test]
fn timestamp_format_parity() {
    assert_eq!(timestamp_format(0.0), "1970-01-01T00:00:00.000Z");
    assert_eq!(timestamp_format(1705327200.0), "2024-01-15T14:00:00.000Z");
}
