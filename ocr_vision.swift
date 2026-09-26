// 画像をmacOS標準のOCR(Visionフレームワーク)にかけ、認識したテキストを標準出力に出す。
// ビルド: swiftc -O ocr_vision.swift -o work/ocr_vision
// 使い方: work/ocr_vision page-1.png page-2.png ...
import Foundation
import Vision
import AppKit

for path in CommandLine.arguments.dropFirst() {
    guard let img = NSImage(contentsOfFile: path),
          let cg = img.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
        FileHandle.standardError.write("読み込み失敗: \(path)\n".data(using: .utf8)!)
        continue
    }
    let req = VNRecognizeTextRequest()
    req.recognitionLevel = .accurate
    req.recognitionLanguages = ["ja-JP", "en-US"]
    req.usesLanguageCorrection = true
    do {
        try VNImageRequestHandler(cgImage: cg, options: [:]).perform([req])
        let lines = (req.results ?? []).compactMap { $0.topCandidates(1).first?.string }
        print("===== \(path) : \(lines.count)行 =====")
        print(lines.joined(separator: "\n"))
    } catch {
        FileHandle.standardError.write("OCR失敗: \(error)\n".data(using: .utf8)!)
    }
}
