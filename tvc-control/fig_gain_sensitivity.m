%% fig_gain_sensitivity.m 
%  Shows the closedloop step response for Kp scaled across the stable range.
%  Demonstrates the valid range Kp in [0.007, 0.073] identified from GM=10.4 dB.
tvc_params;

scales = [0.32, 0.6, 1.0, 2.0, 3.0, 3.3];
labels = {'0.32\times (near lower limit)','0.6\times','1.0\times (nominal)',...
          '2.0\times','3.0\times','3.3\times (near upper limit)'};
colors = [0.7 0.7 0.7; 0.5 0.5 0.8; 0 0.45 0.70; 0.85 0.55 0; 0.8 0.2 0.2; 0.5 0 0];

t = 0:0.005:3;
theta_ref = deg2rad(5);

figure('Color','w','Position',[100 100 560 380]);
hold on;
for i = 1:numel(scales)
    Kp_i = Kp * scales(i);
    Kd_i = Kd * scales(i);
    C_i  = tf([Kp_i+Kd_i*N, Kp_i*N],[1 N]);
    L_i  = C_i*G;
    T_i  = feedback(L_i,1);
    kr_i = 1/dcgain(T_i);
    Tcl_i = kr_i * T_i;
    r_sig = theta_ref*(t>=0.5);
    y = lsim(Tcl_i, r_sig, t);
    plot(t, rad2deg(y), 'LineWidth', 1.3, 'Color', colors(i,:));
end

yline(rad2deg(theta_ref),':k','reference','LabelHorizontalAlignment','left');
grid on;
xlabel('Time (s)'); ylabel('Pitch \theta (deg)');
title('Gain sensitivity: Kp scaled across the stable range');
legend(labels,'Location','southeast','FontSize',8);
set(gca,'FontSize',11);

exportgraphics(gcf,'fig_gain_sensitivity.pdf','ContentType','vector');
disp('saved fig_gain_sensitivity.pdf');
fprintf('Stable range: Kp in [%.3f, %.3f]\n', Kp*0.32, Kp*3.32);
