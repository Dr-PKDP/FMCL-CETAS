package com.example.fmclpilot

import android.os.Bundle
import android.os.SystemClock
import android.util.Log
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf

import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.fmclpilot.ui.theme.FMCLPilotTheme
import java.util.Locale
import java.util.Random
import kotlin.concurrent.thread
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.max

enum class WorkloadLevel(
    val label: String,
    val features: Int,
    val hidden: Int,
    val classes: Int,
    val samples: Int,
    val batch: Int,
    val localEpochs: Int
) {
    COMPACT("Compact", 32, 32, 4, 2000, 32, 5),
    HIGH_LOAD("High-load", 64, 64, 4, 8000, 32, 10)
}

enum class TrainingPolicy(val label: String) {
    CONTINUOUS("Continuous"),
    DUTY_CYCLE("Intermittent 60 s ON / 30 s PAUSE")
}

class MainActivity : ComponentActivity() {
    @Volatile private var running = false

    private var statusText by mutableStateOf("Ready. Select workload and policy, then start training.")
    private var selectedWorkload by mutableStateOf(WorkloadLevel.COMPACT)
    private var selectedPolicy by mutableStateOf(TrainingPolicy.CONTINUOUS)
    private var runningUi by mutableStateOf(false)
    private var completedRounds by mutableIntStateOf(0)
    private var completedEpochs by mutableIntStateOf(0)

    private val tag = "FMCL_PILOT"
    private val activeWindowMs = 60_000L
    private val pauseWindowMs = 30_000L

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        setContent {
            FMCLPilotTheme {
                MaterialTheme {
                    PilotScreen(
                        statusText = statusText,
                        workload = selectedWorkload,
                        policy = selectedPolicy,
                        running = runningUi,
                        rounds = completedRounds,
                        epochs = completedEpochs,
                        onSelectCompact = { if (!runningUi) selectedWorkload = WorkloadLevel.COMPACT },
                        onSelectHighLoad = { if (!runningUi) selectedWorkload = WorkloadLevel.HIGH_LOAD },
                        onSelectContinuous = { if (!runningUi) selectedPolicy = TrainingPolicy.CONTINUOUS },
                        onSelectDutyCycle = { if (!runningUi) selectedPolicy = TrainingPolicy.DUTY_CYCLE },
                        onStart = { startBenchmark(selectedWorkload, selectedPolicy) },
                        onStop = { stopBenchmark() }
                    )
                }
            }
        }
    }

    private fun startBenchmark(config: WorkloadLevel, policy: TrainingPolicy) {
        if (running) return
        running = true
        runningUi = true
        completedRounds = 0
        completedEpochs = 0
        logEvent(
            "TRAINING_START workload=${config.label} policy=${policy.name} " +
                "samples=${config.samples} features=${config.features} hidden=${config.hidden} " +
                "classes=${config.classes} local_epochs=${config.localEpochs} batch=${config.batch} " +
                "dataset_seed=20260919 model_reset_each_round=true " +
                "active_window_ms=$activeWindowMs pause_window_ms=$pauseWindowMs"
        )
        statusText = "Training started: ${config.label}\nPolicy: ${policy.label}"

        thread(name = "fmcl-${config.label.lowercase(Locale.US)}-${policy.name.lowercase(Locale.US)}") {
            val dataset = SyntheticDataset(config)
            when (policy) {
                TrainingPolicy.CONTINUOUS -> runContinuousTraining(config, dataset)
                TrainingPolicy.DUTY_CYCLE -> runDutyCycleTraining(config, dataset)
            }
            logEvent("TRAINING_STOP workload=${config.label} policy=${policy.name} rounds=$completedRounds epochs=$completedEpochs")
            runOnUiThread {
                statusText = "Stopped: ${config.label}\nPolicy: ${policy.label}\n\nRounds completed: $completedRounds\nEpochs completed: $completedEpochs"
                runningUi = false
            }
        }
    }

    private fun runContinuousTraining(config: WorkloadLevel, dataset: SyntheticDataset) {
        logEvent("DUTY_ACTIVE workload=${config.label} policy=CONTINUOUS cycle=0")
        while (running) completeOneRound(config, dataset, TrainingPolicy.CONTINUOUS)
    }

    private fun runDutyCycleTraining(config: WorkloadLevel, dataset: SyntheticDataset) {
        var cycle = 0
        while (running) {
            cycle += 1
            val activeStart = SystemClock.elapsedRealtime()
            logEvent("DUTY_ACTIVE workload=${config.label} policy=DUTY_CYCLE cycle=$cycle planned_active_ms=$activeWindowMs")
            updateStatus("Active: ${config.label}\nPolicy: ${TrainingPolicy.DUTY_CYCLE.label}\nCycle: $cycle\nRounds: $completedRounds | Epochs: $completedEpochs")
            while (running && SystemClock.elapsedRealtime() - activeStart < activeWindowMs) {
                completeOneRound(config, dataset, TrainingPolicy.DUTY_CYCLE)
            }
            if (!running) break

            val pauseStart = SystemClock.elapsedRealtime()
            logEvent("DUTY_PAUSE workload=${config.label} policy=DUTY_CYCLE cycle=$cycle planned_pause_ms=$pauseWindowMs")
            updateStatus("Paused: ${config.label}\nPolicy: ${TrainingPolicy.DUTY_CYCLE.label}\nCycle: $cycle\nRounds: $completedRounds | Epochs: $completedEpochs")
            while (running && SystemClock.elapsedRealtime() - pauseStart < pauseWindowMs) Thread.sleep(200)
            if (running) logEvent("DUTY_RESUME workload=${config.label} policy=DUTY_CYCLE next_cycle=${cycle + 1}")
        }
    }

    private fun completeOneRound(config: WorkloadLevel, dataset: SyntheticDataset, policy: TrainingPolicy) {
        val result = NeuralTrainer(config, dataset, completedRounds).runRound()
        completedRounds += 1
        completedEpochs += config.localEpochs
        logEvent(
            "ROUND_COMPLETE workload=${config.label} policy=${policy.name} round=$completedRounds " +
                "epochs=$completedEpochs loss=${format(result.loss)} accuracy=${format(result.accuracy)} " +
                "update_l2=${format(result.updateL2)} duration_ms=${result.durationMs}"
        )
        updateStatus(
            "Training active: ${config.label}\nPolicy: ${policy.label}\nRounds: $completedRounds | Epochs: $completedEpochs\n" +
                "Loss: ${format(result.loss)} | Accuracy: ${format(result.accuracy)}\n" +
                "Update L2: ${format(result.updateL2)} | Last round: ${result.durationMs} ms"
        )
    }

    private fun stopBenchmark() {
        if (!running) return
        running = false
        statusText = "Stopping after the current round or pause check..."
    }

    private fun updateStatus(text: String) {
        runOnUiThread { statusText = text }
    }

    private fun logEvent(message: String) = Log.i(tag, message)
    private fun format(value: Double): String = String.format(Locale.US, "%.4f", value)
}

@androidx.compose.runtime.Composable
private fun PilotScreen(
    statusText: String,
    workload: WorkloadLevel,
    policy: TrainingPolicy,
    running: Boolean,
    rounds: Int,
    epochs: Int,
    onSelectCompact: () -> Unit,
    onSelectHighLoad: () -> Unit,
    onSelectContinuous: () -> Unit,
    onSelectDutyCycle: () -> Unit,
    onStart: () -> Unit,
    onStop: () -> Unit
) {
    val scrollState = rememberScrollState()
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(scrollState)
            .padding(horizontal = 16.dp, vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Top
    ) {
        Text("FMCL Local Training Pilot", fontSize = 21.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(8.dp))
        Text("Workload: ${workload.label}", fontSize = 15.sp, fontWeight = FontWeight.Bold)
        Text("Policy: ${policy.label}", fontSize = 13.sp)
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onSelectCompact, enabled = !running, modifier = Modifier.weight(1f)) { Text("COMPACT", fontSize = 12.sp) }
            OutlinedButton(onClick = onSelectHighLoad, enabled = !running, modifier = Modifier.weight(1f)) { Text("HIGH-LOAD", fontSize = 12.sp) }
        }
        Spacer(Modifier.height(6.dp))
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = onSelectContinuous, enabled = !running, modifier = Modifier.weight(1f)) { Text("CONTINUOUS", fontSize = 11.sp) }
            OutlinedButton(onClick = onSelectDutyCycle, enabled = !running, modifier = Modifier.weight(1f)) { Text("60s ON / 30s PAUSE", fontSize = 10.sp) }
        }
        Spacer(Modifier.height(10.dp))
        Text(statusText, fontSize = 14.sp, modifier = Modifier.fillMaxWidth())
        Spacer(Modifier.height(6.dp))
        Text("Rounds: $rounds | Epochs: $epochs", fontSize = 13.sp)
        Spacer(Modifier.height(12.dp))
        Button(onClick = onStart, enabled = !running, modifier = Modifier.fillMaxWidth()) { Text("START LOCAL TRAINING", fontSize = 15.sp) }
        Spacer(Modifier.height(8.dp))
        Button(onClick = onStop, enabled = running, modifier = Modifier.fillMaxWidth()) { Text("STOP", fontSize = 15.sp) }
        Spacer(Modifier.height(8.dp))
    }
}

data class RoundResult(val loss: Double, val accuracy: Double, val updateL2: Double, val durationMs: Long)

class SyntheticDataset(private val config: WorkloadLevel) {
    val x = Array(config.samples) { DoubleArray(config.features) }
    val y = IntArray(config.samples)

    init {
        val random = Random(20260919L + config.features)
        val trueWeights = Array(config.classes) { DoubleArray(config.features) { random.nextGaussian() * 0.75 } }
        for (i in 0 until config.samples) {
            for (j in 0 until config.features) x[i][j] = random.nextGaussian()
            val logits = DoubleArray(config.classes)
            for (c in 0 until config.classes) {
                var score = 0.0
                for (j in 0 until config.features) score += trueWeights[c][j] * x[i][j]
                logits[c] = score + random.nextGaussian() * 0.8
            }
            y[i] = argMax(logits)
        }
    }

    private fun argMax(values: DoubleArray): Int {
        var best = 0
        for (i in 1 until values.size) if (values[i] > values[best]) best = i
        return best
    }
}

class NeuralTrainer(private val config: WorkloadLevel, private val dataset: SyntheticDataset, roundIndex: Int) {
    private val learningRate = 0.015
    private val random = Random(700000L + roundIndex)
    private val w1 = Array(config.hidden) { DoubleArray(config.features) { random.nextGaussian() * 0.05 } }
    private val b1 = DoubleArray(config.hidden)
    private val w2 = Array(config.classes) { DoubleArray(config.hidden) { random.nextGaussian() * 0.05 } }
    private val b2 = DoubleArray(config.classes)
    private val initialW1 = Array(config.hidden) { h -> w1[h].clone() }
    private val initialB1 = b1.clone()
    private val initialW2 = Array(config.classes) { c -> w2[c].clone() }
    private val initialB2 = b2.clone()

    fun runRound(): RoundResult {
        val startedAt = SystemClock.elapsedRealtime()
        repeat(config.localEpochs) {
            var start = 0
            while (start < config.samples) {
                val end = minOf(start + config.batch, config.samples)
                trainBatch(start, end)
                start = end
            }
        }
        val metrics = evaluate()
        return RoundResult(metrics.first, metrics.second, calculateUpdateL2(), SystemClock.elapsedRealtime() - startedAt)
    }

    private fun trainBatch(start: Int, end: Int) {
        val gradW1 = Array(config.hidden) { DoubleArray(config.features) }
        val gradB1 = DoubleArray(config.hidden)
        val gradW2 = Array(config.classes) { DoubleArray(config.hidden) }
        val gradB2 = DoubleArray(config.classes)
        val hiddenPre = DoubleArray(config.hidden)
        val hidden = DoubleArray(config.hidden)
        val logits = DoubleArray(config.classes)
        val probabilities = DoubleArray(config.classes)
        val deltaOut = DoubleArray(config.classes)
        val batchSize = (end - start).toDouble()
        for (i in start until end) {
            forward(dataset.x[i], hiddenPre, hidden, logits, probabilities)
            for (c in 0 until config.classes) {
                deltaOut[c] = probabilities[c] - if (dataset.y[i] == c) 1.0 else 0.0
                gradB2[c] += deltaOut[c]
                for (h in 0 until config.hidden) gradW2[c][h] += deltaOut[c] * hidden[h]
            }
            for (h in 0 until config.hidden) {
                var hiddenDelta = 0.0
                for (c in 0 until config.classes) hiddenDelta += deltaOut[c] * w2[c][h]
                if (hiddenPre[h] <= 0.0) hiddenDelta = 0.0
                gradB1[h] += hiddenDelta
                for (j in 0 until config.features) gradW1[h][j] += hiddenDelta * dataset.x[i][j]
            }
        }
        for (c in 0 until config.classes) {
            b2[c] -= learningRate * gradB2[c] / batchSize
            for (h in 0 until config.hidden) w2[c][h] -= learningRate * gradW2[c][h] / batchSize
        }
        for (h in 0 until config.hidden) {
            b1[h] -= learningRate * gradB1[h] / batchSize
            for (j in 0 until config.features) w1[h][j] -= learningRate * gradW1[h][j] / batchSize
        }
    }

    private fun evaluate(): Pair<Double, Double> {
        var loss = 0.0
        var correct = 0
        val hiddenPre = DoubleArray(config.hidden)
        val hidden = DoubleArray(config.hidden)
        val logits = DoubleArray(config.classes)
        val probabilities = DoubleArray(config.classes)
        for (i in 0 until config.samples) {
            forward(dataset.x[i], hiddenPre, hidden, logits, probabilities)
            loss += -ln(probabilities[dataset.y[i]].coerceIn(1e-12, 1.0))
            if (argMax(probabilities) == dataset.y[i]) correct += 1
        }
        return Pair(loss / config.samples, correct.toDouble() / config.samples)
    }

    private fun forward(input: DoubleArray, hiddenPre: DoubleArray, hidden: DoubleArray, logits: DoubleArray, probabilities: DoubleArray) {
        for (h in 0 until config.hidden) {
            var value = b1[h]
            for (j in 0 until config.features) value += w1[h][j] * input[j]
            hiddenPre[h] = value
            hidden[h] = max(0.0, value)
        }
        for (c in 0 until config.classes) {
            var value = b2[c]
            for (h in 0 until config.hidden) value += w2[c][h] * hidden[h]
            logits[c] = value
        }
        softmax(logits, probabilities)
    }

    private fun softmax(logits: DoubleArray, probabilities: DoubleArray) {
        var maximum = logits[0]
        for (i in 1 until logits.size) if (logits[i] > maximum) maximum = logits[i]
        var sum = 0.0
        for (i in logits.indices) {
            probabilities[i] = exp(logits[i] - maximum)
            sum += probabilities[i]
        }
        for (i in probabilities.indices) probabilities[i] /= sum
    }

    private fun calculateUpdateL2(): Double {
        var squared = 0.0
        for (h in 0 until config.hidden) {
            val db = b1[h] - initialB1[h]
            squared += db * db
            for (j in 0 until config.features) {
                val d = w1[h][j] - initialW1[h][j]
                squared += d * d
            }
        }
        for (c in 0 until config.classes) {
            val db = b2[c] - initialB2[c]
            squared += db * db
            for (h in 0 until config.hidden) {
                val d = w2[c][h] - initialW2[c][h]
                squared += d * d
            }
        }
        return kotlin.math.sqrt(squared)
    }

    private fun argMax(values: DoubleArray): Int {
        var best = 0
        for (i in 1 until values.size) if (values[i] > values[best]) best = i
        return best
    }
}
