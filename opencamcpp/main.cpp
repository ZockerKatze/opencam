#include <opencv2/opencv.hpp>
#ifdef WITH_CUDA
#include <opencv2/cudaimgproc.hpp>
#include <opencv2/cudawarping.hpp>
#include <opencv2/cudaobjdetect.hpp>
#include <opencv2/cudabgsegm.hpp>
#include <opencv2/cudacodec.hpp>
#include <opencv2/core/cuda.hpp>
#endif
#include <QApplication>
#include <QMainWindow>
#include <QLabel>
#include <QPushButton>
#include <QVBoxLayout>
#include <QComboBox>
#include <QMessageBox>
#include <QProgressDialog>
#include <QTimer>
#include <QThread>
#include <QString>
#include <QFile>
#include <QProgressBar>
#include <QDialog>
#include <memory>
#include <vector>
#include <string>
#include <thread>
#include <atomic>
#include <queue>
#include <mutex>
#include <condition_variable>

class FrameProcessor : public QThread {
    Q_OBJECT
public:
    FrameProcessor(QObject* parent = nullptr) : QThread(parent), running(false) {
        #ifdef WITH_CUDA
        // Initialize CUDA device
        cv::cuda::setDevice(0);
        stream = cv::cuda::Stream();
        #endif
    }

    void startProcessing() {
        running = true;
        if (!isRunning()) start();
    }

    void stopProcessing() {
        running = false;
        wait();
    }

    void setNet(cv::dnn::Net& net) {
        std::lock_guard<std::mutex> lock(netMutex);
        this->net = net;
    }

    void queueFrame(const cv::Mat& frame) {
        std::lock_guard<std::mutex> lock(queueMutex);
        frameQueue.push(frame);
        condition.notify_one();
    }

signals:
    void frameProcessed(QImage image);

protected:
    void run() override {
        while (running) {
            cv::Mat frame;
            {
                std::unique_lock<std::mutex> lock(queueMutex);
                condition.wait(lock, [this] { return !frameQueue.empty() || !running; });
                if (!running) break;
                frame = frameQueue.front();
                frameQueue.pop();
            }

            if (frame.empty()) continue;

            #ifdef WITH_CUDA
            // GPU processing path
            cv::cuda::GpuMat gpuFrame;
            gpuFrame.upload(frame, stream);

            cv::cuda::GpuMat gpuResized;
            cv::cuda::resize(gpuFrame, gpuResized, cv::Size(416, 416), 0, 0, cv::INTER_CUBIC, stream);

            // Download for DNN processing (until we implement CUDA DNN)
            cv::Mat resized;
            gpuResized.download(resized, stream);
            #else
            // CPU processing path
            cv::Mat resized;
            cv::resize(frame, resized, cv::Size(416, 416), 0, 0, cv::INTER_CUBIC);
            #endif

            // Object detection
            cv::Mat blob;
            cv::dnn::blobFromImage(resized, blob, 1/255.0, cv::Size(416, 416), cv::Scalar(0,0,0), true, false);
            
            {
                std::lock_guard<std::mutex> lock(netMutex);
                net.setInput(blob);
                std::vector<cv::Mat> outs;
                net.forward(outs, net.getUnconnectedOutLayersNames());

                std::vector<int> classIds;
                std::vector<float> confidences;
                std::vector<cv::Rect> boxes;

                for (const auto& out : outs) {
                    float* data = (float*)out.data;
                    for (int j = 0; j < out.rows; ++j, data += out.cols) {
                        cv::Mat scores = out.row(j).colRange(5, out.cols);
                        cv::Point classIdPoint;
                        double confidence;
                        cv::minMaxLoc(scores, 0, &confidence, 0, &classIdPoint);

                        if (confidence > 0.5) {
                            int centerX = (int)(data[0] * frame.cols);
                            int centerY = (int)(data[1] * frame.rows);
                            int width = (int)(data[2] * frame.cols);
                            int height = (int)(data[3] * frame.rows);
                            int left = centerX - width / 2;
                            int top = centerY - height / 2;

                            classIds.push_back(classIdPoint.x);
                            confidences.push_back((float)confidence);
                            boxes.push_back(cv::Rect(left, top, width, height));
                        }
                    }
                }

                std::vector<int> indices;
                cv::dnn::NMSBoxes(boxes, confidences, 0.5, 0.4, indices);

                for (size_t i = 0; i < indices.size(); ++i) {
                    int idx = indices[i];
                    cv::Rect box = boxes[idx];
                    cv::rectangle(frame, box, cv::Scalar(0, 255, 0), 2);
                }
            }

            #ifdef WITH_CUDA
            // Convert to RGB on GPU
            cv::cuda::GpuMat gpuRGB;
            cv::cuda::cvtColor(gpuFrame, gpuRGB, cv::COLOR_BGR2RGB, 0, stream);
            cv::Mat rgb;
            gpuRGB.download(rgb, stream);
            #else
            // Convert to RGB on CPU
            cv::Mat rgb;
            cv::cvtColor(frame, rgb, cv::COLOR_BGR2RGB);
            #endif

            // Convert to QImage
            QImage qimg(rgb.data, rgb.cols, rgb.rows, rgb.step, QImage::Format_RGB888);
            emit frameProcessed(qimg.copy());
        }
    }

private:
    std::atomic<bool> running;
    #ifdef WITH_CUDA
    cv::cuda::Stream stream;
    #endif
    cv::dnn::Net net;
    std::queue<cv::Mat> frameQueue;
    std::mutex queueMutex;
    std::mutex netMutex;
    std::condition_variable condition;
};

class CameraApp : public QMainWindow {
    Q_OBJECT
public:
    CameraApp(QWidget* parent = nullptr) : QMainWindow(parent) {
        setWindowTitle("GPU-Accelerated Object Detection");
        setGeometry(100, 100, 1280, 720);

        #ifdef WITH_CUDA
        // Check CUDA device
        int deviceCount = cv::cuda::getCudaEnabledDeviceCount();
        if (deviceCount == 0) {
            QMessageBox::warning(this, "Warning", "No CUDA capable devices found. Falling back to CPU processing.");
        } else {
            cv::cuda::printCudaDeviceInfo(0);
        }
        #endif

        setupUI();
        initializeObjectDetection();
        processor = new FrameProcessor(this);
        connect(processor, &FrameProcessor::frameProcessed, this, &CameraApp::updateFrame);
    }

    ~CameraApp() {
        stopCamera();
        if (processor) {
            processor->stopProcessing();
            delete processor;
        }
    }

private slots:
    void startCamera() {
        if (!cap.isOpened()) {
            cap.open(currentCamera);
            cap.set(cv::CAP_PROP_FRAME_WIDTH, 1920);
            cap.set(cv::CAP_PROP_FRAME_HEIGHT, 1080);
            cap.set(cv::CAP_PROP_FPS, 120); // Request maximum FPS
            
            #ifdef WITH_CUDA
            // Try to use CUDA video decoder if available
            cap.set(cv::CAP_PROP_CUDA_DEVICE, 0);
            #endif
            
            if (!cap.isOpened()) {
                QMessageBox::critical(this, "Error", "Failed to open camera!");
                return;
            }
        }

        processor->startProcessing();
        timer->start(0); // Run as fast as possible
    }

    void stopCamera() {
        timer->stop();
        processor->stopProcessing();
        if (cap.isOpened()) {
            cap.release();
        }
    }

    void captureFrame() {
        if (!cap.isOpened()) return;

        cv::Mat frame;
        cap >> frame;
        if (frame.empty()) return;

        processor->queueFrame(frame);
    }

    void updateFrame(const QImage& image) {
        QPixmap pixmap = QPixmap::fromImage(image);
        videoLabel->setPixmap(pixmap.scaled(videoLabel->size(), Qt::KeepAspectRatio, Qt::SmoothTransformation));
    }

private:
    void setupUI() {
        QWidget* centralWidget = new QWidget(this);
        setCentralWidget(centralWidget);
        QVBoxLayout* layout = new QVBoxLayout(centralWidget);

        videoLabel = new QLabel(this);
        videoLabel->setMinimumSize(640, 480);
        layout->addWidget(videoLabel);

        cameraSelect = new QComboBox(this);
        detectCameras();
        layout->addWidget(cameraSelect);

        startButton = new QPushButton("Start Camera", this);
        connect(startButton, &QPushButton::clicked, this, &CameraApp::startCamera);
        layout->addWidget(startButton);

        stopButton = new QPushButton("Stop Camera", this);
        connect(stopButton, &QPushButton::clicked, this, &CameraApp::stopCamera);
        layout->addWidget(stopButton);

        timer = new QTimer(this);
        connect(timer, &QTimer::timeout, this, &CameraApp::captureFrame);
    }

    void detectCameras() {
        for (int i = 0; i < 10; ++i) {
            cv::VideoCapture temp(i);
            if (temp.isOpened()) {
                cameraSelect->addItem("Camera " + QString::number(i), i);
                temp.release();
            }
        }
    }

    void initializeObjectDetection() {
        // Download and load YOLO model (implementation similar to Python version)
        // ...
    }

    QLabel* videoLabel;
    QComboBox* cameraSelect;
    QPushButton* startButton;
    QPushButton* stopButton;
    QTimer* timer;
    cv::VideoCapture cap;
    int currentCamera = 0;
    FrameProcessor* processor;
};

#include "main.moc"

int main(int argc, char* argv[]) {
    QApplication app(argc, argv);
    CameraApp window;
    window.show();
    return app.exec();
} 