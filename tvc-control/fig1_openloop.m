%% fig1_openloop.m  
%  Open-loop response to a small initial tilt, showing divergence in ~1 s.
%  Demonstrates the openloop instablity (RHP pole at +1.06).

tvc_params;

% Simulate the OPENLOOP linear system from a small initial pitch tilt.
% No control input (delta_c = 0); initial theta = 2 deg.
x0 = [deg2rad(2); 0; 0; 0];     % [theta; thetadot; delta; deltadot]
t  = 0:0.01:3;
u  = zeros(size(t));            % no control
[y,~,~] = lsim(sys_ss, u, t, x0);

figure('Color','w','Position',[100 100 560 360]);
plot(t, rad2deg(y), 'LineWidth', 1.6); grid on;
xlabel('Time (s)'); ylabel('Pitch angle \theta (deg)');
title('Open-loop response to a 2^\circ initial tilt');
% mark the time constant
hold on; xline(1/sqrt(mu_a),'--',sprintf('1/\\surd\\mu_a = %.2f s',1/sqrt(mu_a)),...
    'LabelOrientation','horizontal');
set(gca,'FontSize',11);

% Export
exportgraphics(gcf,'fig_openloop.pdf','ContentType','vector');
disp('saved fig_openloop.pdf');
